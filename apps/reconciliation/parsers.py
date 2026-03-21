import csv
import logging
import pandas as pd
import io
import hashlib
import collections
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from .models import RTAFile, Transaction, Holding, FailedRTARecord
from apps.products.models import Scheme
from apps.users.models import InvestorProfile
from apps.investments.models import Folio
from apps.reconciliation.utils.reconcile import recalculate_holding, get_cams_transaction_type_and_action, get_karvy_transaction_type_and_action
from apps.reconciliation.utils.fingerprint import generate_cams_fingerprint, generate_karvy_fingerprint

User = get_user_model()
logger = logging.getLogger(__name__)

class BaseParser:
    """
    Base parser containing shared logic for all RTA mailback parsers.
    """
    def __init__(self, rta_file_obj=None, file_path=None):
        self.rta_file = rta_file_obj
        self.file_path = file_path
        if not self.file_path and self.rta_file:
            self.file_path = self.rta_file.file.path

        self.impacted_holdings = set()
        self.txn_counts = collections.defaultdict(int)

        self.failed_rows = []

        # Caches to avoid DB hits in loops
        self._scheme_cache = {}
        self._investor_cache = {}
        self._folio_cache = set()

        # Flag to indicate if this is a retry of a failed record.
        # If True, we skip file-level completion logic (like updating RTAFile status)
        # and skip creating duplicate FailedRTARecord entries.
        self.is_retry = False

    def parse(self):
        raise NotImplementedError

    def preload_cache(self, df, pan_col='pan', scheme_col='prodcode', folio_col='folio_no'):
        """
        Preloads Investors, Schemes, and Folios into cache using IN queries to speed up parsing.
        """
        if df is None or df.empty: return

        # 1. Preload Investors
        if pan_col in df.columns:
            pans = df[pan_col].dropna().astype(str).str.upper().str.strip().unique()
            investors = InvestorProfile.objects.filter(pan__in=pans)
            for inv in investors:
                self._investor_cache[inv.pan] = inv

        # 2. Preload Schemes
        if scheme_col in df.columns:
            scheme_codes = df[scheme_col].dropna().astype(str).str.strip().unique()
            schemes = Scheme.objects.filter(channel_partner_code__in=scheme_codes)
            for scheme in schemes:
                if scheme.channel_partner_code:
                    self._scheme_cache[f"{scheme.channel_partner_code}_None"] = scheme

            # Fallback
            schemes_rta = Scheme.objects.filter(rta_scheme_code__in=scheme_codes)
            for scheme in schemes_rta:
                if scheme.rta_scheme_code:
                    self._scheme_cache[f"{scheme.rta_scheme_code}_None"] = scheme

        # 3. Preload Folios
        if folio_col in df.columns:
            folios = df[folio_col].dropna().astype(str).str.strip().unique()
            existing_folios = Folio.objects.filter(folio_number__in=folios).select_related('investor', 'amc')
            for f in existing_folios:
                cache_key = f"{f.investor.id}_{f.amc.id}_{f.folio_number}"
                self._folio_cache.add(cache_key)

    def save_error_file(self):
        """
        Generates an Excel file from failed rows and saves it to the RTAFile model.
        """
        if not self.failed_rows or not self.rta_file:
            return

        if self.is_retry:
            return

        try:
            # Also save errors to FailedRTARecord
            for row_dict in self.failed_rows:
                # Need to handle NaN properly for JSON parsing
                clean_row = {}
                for k, v in row_dict.items():
                    if k == 'error':
                        continue
                    if pd.isna(v):
                        clean_row[k] = None
                    elif isinstance(v, (datetime, pd.Timestamp)):
                        clean_row[k] = v.isoformat()
                    else:
                        clean_row[k] = str(v)

                FailedRTARecord.objects.create(
                    source_file=self.rta_file,
                    rta_type=self.rta_file.rta_type if self.rta_file else 'UNKNOWN',
                    original_txn_number=clean_row.get('trxnno') or clean_row.get('transaction number') or clean_row.get(6),
                    folio_number=clean_row.get('folio_no') or clean_row.get('folio number') or clean_row.get(3),
                    row_data=clean_row,
                    error_reason=str(row_dict.get('error', 'Unknown Error'))
                )

            df = pd.DataFrame(self.failed_rows)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Errors')

            output.seek(0)
            file_name = f"errors_{self.rta_file.id}_{int(timezone.now().timestamp())}.xlsx"
            self.rta_file.error_file.save(file_name, ContentFile(output.read()), save=False)
            self.rta_file.save()
            logger.info(f"Saved error file {file_name} for RTA File {self.rta_file.id}")
        except Exception as e:
            logger.error(f"Failed to generate error file for RTA File {self.rta_file.id}: {e}")

    def parse_date(self, date_str):
        """Attempts to parse date from common formats."""
        if date_str is None or pd.isna(date_str):
            return None
        # Handle Pandas timestamp
        if isinstance(date_str, (pd.Timestamp, datetime)):
            return date_str.date()

        date_str = str(date_str).strip()
        if date_str == '' or date_str.lower() in ('nat', 'nan'):
            return None

        formats = ["%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None

    def clean_decimal(self, value):
        """Cleans and returns a Decimal from string."""
        if value is None:
            return Decimal(0)

        # Handle Pandas NaN/NaT
        if pd.isna(value):
            return Decimal(0)

        val_str = str(value).strip()
        if val_str == '' or val_str.lower() == 'nan':
            return Decimal(0)

        try:
            return Decimal(val_str.replace(',', ''))
        except:
            return Decimal(0)

    def _legacy_generate_fingerprint(self, values):
        """
        Generates a unique hash based on a list of row values.
        Used to uniquely identify rows even if they share the same Transaction No.
        """
        raw_str = "|".join([str(v).strip().upper() if v is not None else "" for v in values])
        return hashlib.md5(raw_str.encode('utf-8')).hexdigest()

    def get_or_create_folio(self, investor, scheme, folio_number):
        if investor and scheme and folio_number:
            cache_key = f"{investor.id}_{scheme.amc.id}_{folio_number}"
            if cache_key not in self._folio_cache:
                Folio.objects.get_or_create(
                    investor=investor,
                    amc=scheme.amc,
                    folio_number=folio_number
                )
                self._folio_cache.add(cache_key)

    def get_or_create_provisional_investor(self, pan, name=None, is_offline=True):
        """
        Finds an investor by PAN or creates a provisional one. Uses cache.
        """
        if not pan:
            return None
        pan = pan.upper().strip()

        if pan in self._investor_cache:
            return self._investor_cache[pan]

        try:
            profile = InvestorProfile.objects.get(pan=pan)
            self._investor_cache[pan] = profile
            return profile
        except InvestorProfile.DoesNotExist:

            # Split Name Logic
            firstname = ""
            middlename = ""
            lastname = ""

            if name:
                parts = name.strip().split()
                if len(parts) == 1:
                    firstname = parts[0]
                elif len(parts) == 2:
                    firstname = parts[0]
                    lastname = parts[1]
                elif len(parts) > 2:
                    firstname = parts[0]
                    lastname = parts[-1]
                    middlename = " ".join(parts[1:-1])

            # Check if User exists (rare case where User exists but no Profile)
            user = User.objects.filter(username=pan).first()
            if not user:
                # Create User
                email = f"{pan}@placeholder.com"
                user = User.objects.create_user(username=pan, email=email, password=pan)
                user.user_type = User.Types.INVESTOR
                if name:
                    user.name = name
                user.save()

            # Create Profile
            # Note: Detailed fields will be filled later via BSE Client Master sync
            try:
                profile = InvestorProfile.objects.get(user=user)
            except InvestorProfile.DoesNotExist:
                profile = InvestorProfile.objects.create(
                    user=user,
                    pan=pan,
                    firstname=firstname,
                    middlename=middlename,
                    lastname=lastname,
                    kyc_status=False, # Assumption until verified
                    is_offline=is_offline
                )
                logger.info(f"Created provisional investor for PAN {pan}")

            self._investor_cache[pan] = profile
            return profile

    def get_scheme(self, scheme_code, isin=None):
        """
        Tries to find scheme by Code (BSE/RTA) or ISIN. Uses cache.
        """
        cache_key = f"{scheme_code}_{isin}"
        if cache_key in self._scheme_cache:
            return self._scheme_cache[cache_key]

        scheme = None
        if scheme_code:
            scheme_code = str(scheme_code).strip()
            scheme = Scheme.objects.filter(channel_partner_code=scheme_code).first()
            if not scheme:
                # Try RTA Scheme Code match if we had such field populated
                scheme = Scheme.objects.filter(rta_scheme_code=scheme_code).first()

        if not scheme and isin:
            scheme = Scheme.objects.filter(isin=isin).first()

        self._scheme_cache[cache_key] = scheme
        return scheme

    def match_or_create_transaction(self, investor, scheme, folio_number, fingerprint, date, amount, units, txn_type, rta_code,
                                    description="", tr_flag="", txn_number=None, nav=None,
                                    raw_data=None,
                                    parsed_txn_type=None,
                                    parsed_txn_action=None,
                                    broker_code=None, sub_broker_code=None, euin=None,
                                    bank_account_no=None, bank_name=None, payment_mode=None, instrument_no=None, instrument_date=None,
                                    load_amount=None, tax_amount=None, stt=None, stamp_duty=None,
                                    status_desc=None, remarks=None, location=None,
                                    # New fields
                                    amc_code=None, product_code=None, txn_nature=None, tax_status=None, micr_no=None, old_folio=None,
                                    reinvest_flag=None, mult_brok=None, scan_ref_no=None, pan=None, min_no=None, targ_src_scheme=None,
                                    ticob_trtype=None, ticob_trno=None, ticob_posted_date=None, dp_id=None, trxn_charges=None,
                                    eligib_amt=None, src_of_txn=None, trxn_suffix=None, siptrxnno=None, ter_location=None,
                                    euin_valid=None, euin_opted=None, sub_brk_arn=None, exch_dc_flag=None, src_brk_code=None,
                                    sys_regn_date=None, ac_no=None, reversal_code=None, exchange_flag=None, ca_initiated_date=None,
                                    gst_state_code=None, igst_amount=None, cgst_amount=None, sgst_amount=None
                                    ):
        """
        Matches incoming RTA transaction with existing (Provisional) BSE transaction,
        or creates a new one. Updates existing RTA transactions if changed.
        """
        if not txn_number:
            return

        # Prepare extra fields dict for update/create
        extra_fields = {
            'raw_data': raw_data or {},
            'broker_code': broker_code,
            'sub_broker_code': sub_broker_code,
            'euin': euin,
            'bank_account_no': bank_account_no,
            'bank_name': bank_name,
            'payment_mode': payment_mode,
            'instrument_no': instrument_no,
            'instrument_date': instrument_date,
            'load_amount': load_amount or Decimal(0),
            'tax_amount': tax_amount or Decimal(0),
            'status_desc': status_desc,
            'remarks': remarks,
            'location': location,
            # New Mappings
            'amc_code': amc_code,
            'product_code': product_code,
            'txn_nature': txn_nature,
            'tax_status': tax_status,
            'micr_no': micr_no,
            'old_folio': old_folio,
            'reinvest_flag': reinvest_flag,
            'mult_brok': mult_brok,
            'scan_ref_no': scan_ref_no,
            'pan': pan,
            'min_no': min_no,
            'targ_src_scheme': targ_src_scheme,
            'ticob_trtype': ticob_trtype,
            'ticob_trno': ticob_trno,
            'ticob_posted_date': ticob_posted_date,
            'dp_id': dp_id,
            'trxn_charges': trxn_charges or Decimal(0),
            'eligib_amt': eligib_amt or Decimal(0),
            'src_of_txn': src_of_txn,
            'trxn_suffix': trxn_suffix,
            'siptrxnno': siptrxnno,
            'ter_location': ter_location,
            'euin_valid': euin_valid,
            'euin_opted': euin_opted,
            'sub_brk_arn': sub_brk_arn,
            'exch_dc_flag': exch_dc_flag,
            'src_brk_code': src_brk_code,
            'sys_regn_date': sys_regn_date,
            'ac_no': ac_no,
            'reversal_code': reversal_code,
            'exchange_flag': exchange_flag,
            'ca_initiated_date': ca_initiated_date,
            'gst_state_code': gst_state_code,
            'igst_amount': igst_amount or Decimal(0),
            'cgst_amount': cgst_amount or Decimal(0),
            'sgst_amount': sgst_amount or Decimal(0),
        }
        if stt is not None:
            extra_fields['stt'] = stt
        if stamp_duty is not None:
            extra_fields['stamp_duty'] = stamp_duty

        # 1. Deduplication and Collision Handling
        existing_txns = Transaction.objects.filter(
            fingerprint=fingerprint,
            folio_number=folio_number,
            scheme=scheme
        )

        txn_to_update = None
        for existing_txn in existing_txns:
            # If the parser provides a txn_number (like CAMS/Karvy native ID),
            # use it to disambiguate identical same-day transactions.
            # Otherwise, since fingerprint already hashes amount, units, and date,
            # any matching fingerprint without a differing txn_number is an update to the SAME transaction.
            if txn_number and existing_txn.txn_number and existing_txn.txn_number != txn_number:
                continue # This is a separate identical transaction (same-day same-amount)

            txn_to_update = existing_txn
            break

        if txn_to_update:
            # Update fields
            txn_to_update.date = date
            txn_to_update.amount = amount
            txn_to_update.units = units
            txn_to_update.txn_type_code = txn_type
            txn_to_update.rta_code = rta_code
            txn_to_update.description = description
            txn_to_update.tr_flag = tr_flag
            txn_to_update.source = Transaction.SOURCE_RTA
            txn_to_update.is_provisional = False
            if parsed_txn_type:
                txn_to_update.txn_type = parsed_txn_type
            if parsed_txn_action:
                txn_to_update.txn_action = parsed_txn_action
            if nav is not None:
                txn_to_update.nav = nav
            if txn_number:
                txn_to_update.txn_number = txn_number
            if self.rta_file:
                txn_to_update.source_file = self.rta_file

            # Update extra fields
            for key, value in extra_fields.items():
                setattr(txn_to_update, key, value)

            # Optionally update relation if missing
            if not txn_to_update.investor and investor:
                txn_to_update.investor = investor
            if not txn_to_update.scheme and scheme:
                txn_to_update.scheme = scheme

            txn_to_update.save()
            logger.info(f"Updated existing transaction with fingerprint {fingerprint}")

            # Recalculate Holding immediately for updates to mirror legacy behavior
            recalculate_holding(investor, scheme, folio_number)
            return

        # 2. Check for collision and create new Transaction
        if existing_txns.exists():
            # A record with the exact same fingerprint exists, but it wasn't chosen for update
            # (e.g. because txn_number differed). It is a valid secondary transaction.
            import uuid
            fingerprint = f"{fingerprint}-{uuid.uuid4().hex[:6]}"
            logger.info(f"Fingerprint collision detected (same-day identical txn). Modified fingerprint to {fingerprint}")

        # Create New Transaction
        Transaction.objects.create(
                investor=investor,
                scheme=scheme,
                folio_number=folio_number,
                rta_code=rta_code,
                txn_type_code=txn_type,
                txn_type=parsed_txn_type,
                txn_action=parsed_txn_action,
                fingerprint=fingerprint,
                txn_number=txn_number,
                date=date,
                amount=amount,
                units=units,
                description=description,
                tr_flag=tr_flag,
                nav=nav,
                source=Transaction.SOURCE_RTA,
                is_provisional=False,
                source_file=self.rta_file if self.rta_file else None,
                **extra_fields
            )

        # Defer recalculation
        if investor and scheme and folio_number:
            self.impacted_holdings.add((investor, scheme, folio_number))

        # Ensure Folio Exists
        self.get_or_create_folio(investor, scheme, folio_number)

    def process_impacted_holdings(self):
        logger.info(f"Recalculating {len(self.impacted_holdings)} impacted holdings...")
        for investor, scheme, folio_number in self.impacted_holdings:
            try:
                recalculate_holding(investor, scheme, folio_number)
            except Exception as e:
                logger.error(f"Error recalculating holding for {folio_number}: {e}")

class FranklinParser(BaseParser):
    """
    Parses Franklin Templeton Mailback Format.
    """

    def parse(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f, delimiter='|')

                for row in reader:
                    try:
                        with transaction.atomic():
                            if not row or len(row) < 10:
                                continue

                            if "Header" in row[0]: continue

                            # Franklin Layout Assumptions:
                            # 1: Scheme Code, 3: Folio, 5: Type, 6: Trxn No, 7: Units, 8: Amount, 9: Date

                            pan = None
                            if len(row) > 18: pan = row[18].strip()
                            if not pan:
                                if len(row) > 14 and len(row[14]) == 10: pan = row[14].strip()

                            if not pan: continue

                            inv_name = row[4].strip() if len(row) > 4 else None

                            investor = self.get_or_create_provisional_investor(pan, inv_name, is_offline=True)

                            scheme_code = row[1].strip()
                            scheme = self.get_scheme(scheme_code)
                            if not scheme: continue

                            folio_number = row[3].strip()
                            txn_number = row[6].strip()

                            txn_date = self.parse_date(row[9])
                            amount = self.clean_decimal(row[8])
                            units = self.clean_decimal(row[7])
                            txn_type = row[5].strip().upper()

                            # Calculate NAV if missing
                            nav = None
                            if units != 0:
                                nav = abs(amount) / abs(units)

                            # Franklin Best Effort Extraction
                            broker_code = row[12].strip() if len(row) > 12 else None
                            euin = row[25].strip() if len(row) > 25 else None

                            parsed_type, parsed_action = get_karvy_transaction_type_and_action(txn_type, "")

                            # Franklin lacks a specialized fingerprint logic, fallback to hash
                            import hashlib
                            raw_str = f"FRANKLIN|{folio_number}|{scheme_code}|{txn_number}|{txn_date}|{amount}|{units}|{txn_type}"
                            fingerprint = hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

                            self.match_or_create_transaction(
                                investor, scheme, folio_number, fingerprint, txn_date if txn_date else timezone.now().date(),
                                amount, units, txn_type, 'FRANKLIN', txn_number=txn_number, nav=nav,
                                raw_data={'row': row},
                                parsed_txn_type=parsed_type,
                                parsed_txn_action=parsed_action,
                                broker_code=broker_code,
                                euin=euin
                            )
                    except Exception as e:
                        logger.error(f"Error processing Franklin row: {e}")
                        # Convert list row to dict for consistent handling
                        row_dict = {i: val for i, val in enumerate(row)}
                        row_dict['error'] = str(e)
                        self.failed_rows.append(row_dict)

            self.process_impacted_holdings()

            if self.rta_file and not self.is_retry:
                if self.failed_rows:
                     self.save_error_file()

                self.rta_file.status = RTAFile.STATUS_PROCESSED
                self.rta_file.processed_at = timezone.now()
                self.rta_file.save()

        except Exception as e:
            if self.rta_file and not self.is_retry:
                self.rta_file.status = RTAFile.STATUS_FAILED
                self.rta_file.error_log = str(e)
                self.rta_file.save()
            logger.error(f"Franklin Parsing failed: {e}")
            if not getattr(self, 'is_retry', False) and not self.rta_file:
                raise e


class DBFParser(BaseParser):
    """
    Parses .dbf files (CAMS or Karvy) by converting to DataFrame.
    """
    def parse(self):
        try:
            # Load DBF
            from simpledbf import Dbf5
            dbf = Dbf5(self.file_path)
            df = dbf.to_dataframe()

            # Normalize columns to lowercase
            df.columns = df.columns.str.lower()

            # Detect Format - Updated for requested cleanup
            # CAMS detection based on presence of key columns from user list
            if 'prodcode' in df.columns and 'trxnno' in df.columns:
                logger.info("Detected CAMS DBF Format")
                self.parse_cams(df)
            else:
                logger.warning(f"Unknown DBF Format or Legacy Karvy detected (not supported). Columns: {list(df.columns)}")
                # Save error file with unknown format info
                if self.rta_file:
                     self.rta_file.status = RTAFile.STATUS_FAILED
                     self.rta_file.error_log = f"Unknown DBF Format. Columns: {list(df.columns)}"
                     self.rta_file.save()
                return

            self.process_impacted_holdings()

            if self.rta_file and not self.is_retry:
                if self.failed_rows:
                     self.save_error_file()

                self.rta_file.status = RTAFile.STATUS_PROCESSED
                self.rta_file.processed_at = timezone.now()
                self.rta_file.save()

        except Exception as e:
            if self.rta_file and not self.is_retry:
                self.rta_file.status = RTAFile.STATUS_FAILED
                self.rta_file.error_log = str(e)
                self.rta_file.save()
            logger.error(f"DBF Parsing failed: {e}")
            if not getattr(self, 'is_retry', False) and not self.rta_file:
                raise e

    def parse_cams(self, df):
        # CAMS Logic with New Mapping
        self.preload_cache(df, pan_col='pan', scheme_col='prodcode', folio_col='folio_no')
        for _, row in df.iterrows():
                try:
                    with transaction.atomic():
                        # Map Fields from User List (lower cased)
                        pan = str(row.get('pan', '')).strip()
                        if not pan or pan.lower() == 'nan': continue

                        inv_name = str(row.get('inv_name', '')).strip()
                        investor = self.get_or_create_provisional_investor(pan, inv_name, is_offline=True)

                        scheme_code = str(row.get('prodcode', '')).strip()
                        # Fallback to scheme name if code fails? No, rely on mapping
                        scheme = self.get_scheme(scheme_code)
                        if not scheme:
                            logger.warning(f"Scheme not found for CAMS DBF: {scheme_code}")
                            row_dict = row.to_dict()
                            row_dict['error'] = f"Scheme not found: {scheme_code}"
                            self.failed_rows.append(row_dict)
                            continue

                        folio_number = str(row.get('folio_no', '')).strip()
                        txn_number = str(row.get('trxnno', '')).strip()

                        date_val = row.get('traddate')
                        txn_date = self.parse_date(date_val)
                        if not txn_date: continue

                        amount = self.clean_decimal(row.get('amount'))
                        units = self.clean_decimal(row.get('units'))
                        txn_stat = str(row.get('trxnstat', '')).strip()

                        txn_type_code = str(row.get('trxntype', '')).strip()
                        txn_type = str(row.get('trxn_type_', '')).strip()
                        tr_flag = str(row.get('trxnmode', '')).strip()
                        # trxnstat is Transaction Status from list
                        
                        # NAV Calculation
                        nav = None
                        raw_price = row.get('purprice') or row.get('price')
                        if not pd.isna(raw_price):
                            nav = self.clean_decimal(raw_price)
                        if (nav is None or nav == 0) and units != 0:
                            nav = abs(amount) / abs(units)

                        # Fingerprint
                        # Use deterministic, source-aware fingerprint-based deduplication
                        row_dict = {
                            'folio_no': str(row.get('folio_no', '')).strip(),
                            'prodcode': str(row.get('prodcode', '')).strip(),
                            'trxn_type_': str(row.get('trxn_type_', '')).strip(),
                            'trxn_natur': str(row.get('trxn_natur', '')).strip(),
                            'amount': amount,
                            'units': units,
                            'traddate': txn_date,
                            'trxnno': str(row.get('trxnno', '')).strip(),
                            'siptrxnno': str(row.get('siptrxnno', '')).strip(),
                            'trxn_suffi': str(row.get('trxn_suffi', '')).strip(),
                            'scanrefno': str(row.get('scanrefno', '')).strip(),
                            'reversal_c': str(row.get('reversal_c', '')).strip(),
                        }
                        fingerprint = generate_cams_fingerprint(row_dict)

                        # New Fields Extraction
                        amc_code = str(row.get('amc_code', '')).strip()
                        product_code = str(row.get('prodcode', '')).strip() # Note: DBF might just have 'prodcode' which we mapped to scheme_code. Check list: "Product Code" (Field 3) vs "AMC Code" (Field 1). prodcode is Field 3. 
                        
                        # Corrected mapping from code review feedback
                        txn_nature = str(row.get('trxn_natur', '')).strip()
                        
                        tax_status = str(row.get('tax_status', '')).strip()
                        micr_no = str(row.get('micr_no', '')).strip()
                        old_folio = str(row.get('old_folio', '')).strip()
                        reinvest_flag = str(row.get('reinvest_f', '')).strip() # Mapped from REINVEST_F
                        mult_brok = str(row.get('mult_brok', '')).strip()
                        
                        location = str(row.get('location', '')).strip()
                        scan_ref_no = str(row.get('scanrefno', '')).strip() # Mapped from SCANREFNO
                        min_no = str(row.get('inv_iin', '')).strip() # Mapped from INV_IIN (Field 44 MIN in list, INV_IIN in column list) or MIN? Column list says INV_IIN. User list Field 44 is MIN. Assuming INV_IIN maps to MIN.
                        
                        targ_src_scheme = str(row.get('targ_src_s', '')).strip() # TARG_SRC_S
                        ticob_trtype = str(row.get('ticob_trty', '')).strip() # TICOB_TRTY
                        ticob_trno = str(row.get('ticob_trno', '')).strip()
                        ticob_posted_date = self.parse_date(row.get('ticob_post')) # TICOB_POST
                        
                        dp_id = str(row.get('dp_id', '')).strip()
                        trxn_charges = self.clean_decimal(row.get('trxn_charg')) # TRXN_CHARG
                        eligib_amt = self.clean_decimal(row.get('eligib_amt'))
                        src_of_txn = str(row.get('src_of_txn', '')).strip()
                        trxn_suffix = str(row.get('trxn_suffi', '')).strip() # TRXN_SUFFI
                        siptrxnno = str(row.get('siptrxnno', '')).strip()
                        ter_location = str(row.get('ter_locati', '')).strip() # TER_LOCATI
                        
                        euin_valid = str(row.get('euin_valid', '')).strip()
                        euin_opted = str(row.get('euin_opted', '')).strip()
                        sub_brk_arn = str(row.get('sub_brk_ar', '')).strip() # SUB_BRK_AR
                        exch_dc_flag = str(row.get('exch_dc_fl', '')).strip() # EXCH_DC_FL
                        src_brk_code = str(row.get('src_brk_co', '')).strip() # SRC_BRK_CO
                        sys_regn_date = self.parse_date(row.get('sys_regn_d')) # SYS_REGN_D
                        
                        ac_no = str(row.get('ac_no', '')).strip()
                        bank_name = str(row.get('bank_name', '')).strip()
                        reversal_code = str(row.get('reversal_c', '')).strip() # REVERSAL_C
                        exchange_flag = str(row.get('exchange_f', '')).strip() # EXCHANGE_F
                        ca_initiated_date = self.parse_date(row.get('ca_initiat')) # CA_INITIAT
                        
                        gst_state_code = str(row.get('gst_state_', '')).strip() # GST_STATE_
                        igst_amount = self.clean_decimal(row.get('igst_amoun')) # IGST_AMOUN
                        cgst_amount = self.clean_decimal(row.get('cgst_amoun')) # CGST_AMOUN
                        sgst_amount = self.clean_decimal(row.get('sgst_amoun')) # SGST_AMOUN
                        
                        stamp_duty = self.clean_decimal(row.get('stamp_duty'))
                        
                        broker_code = str(row.get('brokcode', '')).strip()
                        sub_broker_code = str(row.get('subbrok', '')).strip()
                        euin = str(row.get('euin', '')).strip()
                        
                        stt = self.clean_decimal(row.get('stt'))
                        load_amount = self.clean_decimal(row.get('load'))
                        tax_amount = self.clean_decimal(row.get('total_tax')) or self.clean_decimal(row.get('tax'))
                        
                        remarks = str(row.get('remarks', '')).strip()
                        description = remarks

                        # Handle NaN values to prevent JSON serialization errors (Postgres rejects NaN)
                        raw_row_data = {k: str(v) if pd.notna(v) else None for k, v in row.items()}

                        _, parsed_action = get_cams_transaction_type_and_action(txn_type_code)

                        self.match_or_create_transaction(
                            investor, scheme, folio_number, fingerprint, txn_date, amount, units, txn_type_code, 'CAMS',
                            description=description, tr_flag=tr_flag, txn_number=txn_number, nav=nav,
                            raw_data=raw_row_data,
                            parsed_txn_type=txn_type,
                            parsed_txn_action=parsed_action,
                            broker_code=broker_code, sub_broker_code=sub_broker_code, euin=euin,
                            bank_name=bank_name,
                            stt=stt, stamp_duty=stamp_duty, load_amount=load_amount, tax_amount=tax_amount,
                            status_desc=txn_stat, remarks=remarks, location=location,
                            # New Fields
                            amc_code=amc_code, product_code=product_code, txn_nature=txn_nature, tax_status=tax_status,
                            micr_no=micr_no, old_folio=old_folio, reinvest_flag=reinvest_flag, mult_brok=mult_brok,
                            scan_ref_no=scan_ref_no, pan=pan, min_no=min_no, targ_src_scheme=targ_src_scheme,
                            ticob_trtype=ticob_trtype, ticob_trno=ticob_trno, ticob_posted_date=ticob_posted_date,
                            dp_id=dp_id, trxn_charges=trxn_charges, eligib_amt=eligib_amt, src_of_txn=src_of_txn,
                            trxn_suffix=trxn_suffix, siptrxnno=siptrxnno, ter_location=ter_location,
                            euin_valid=euin_valid, euin_opted=euin_opted, sub_brk_arn=sub_brk_arn,
                            exch_dc_flag=exch_dc_flag, src_brk_code=src_brk_code, sys_regn_date=sys_regn_date,
                            ac_no=ac_no, reversal_code=reversal_code, exchange_flag=exchange_flag,
                            ca_initiated_date=ca_initiated_date, gst_state_code=gst_state_code,
                            igst_amount=igst_amount, cgst_amount=cgst_amount, sgst_amount=sgst_amount
                        )
                except Exception as e:
                    logger.error(f"Error processing CAMS DBF row: {e}")
                    row_dict = row.to_dict()
                    row_dict['error'] = str(e)
                    self.failed_rows.append(row_dict)

class KarvyCSVParser(BaseParser):
    """
    Parses Karvy CSV Format (e.g. MFSD307 and other CSV exports).
    """
    def parse(self):
        try:
            # Read CSV
            df = pd.read_csv(self.file_path)
            # Normalize columns to lowercase and strip whitespace
            df.columns = df.columns.str.lower().str.strip()

            self.preload_cache(df, pan_col='pan1', scheme_col='product code', folio_col='folio number')

            for _, row in df.iterrows():
                try:
                    with transaction.atomic():
                        # Map columns
                        # 'pan1' -> pan
                        pan = str(row.get('pan1', '')).strip()
                        if not pan or pan.lower() == 'nan': continue

                        inv_name = str(row.get('investor name', '')).strip()
                        investor = self.get_or_create_provisional_investor(pan, inv_name, is_offline=True)

                        # 'scheme code'
                        scheme_code = str(row.get('product code', '')).strip()
                        if not scheme_code or scheme_code.lower() == 'nan':
                             # Fallback to Product Code if needed
                             scheme_code = str(row.get('scheme code', '')).strip()

                        isin = str(row.get('isin', '')).strip()

                        scheme = self.get_scheme(scheme_code, isin)
                        if not scheme:
                            logger.warning(f"Scheme not found for Karvy CSV: {scheme_code}")
                            row_dict = row.to_dict()
                            row_dict['error'] = f"Scheme not found: {scheme_code}"
                            self.failed_rows.append(row_dict)
                            continue

                        folio_number = str(row.get('folio number', '')).strip()
                        txn_number = str(row.get('transaction number', '')).strip()

                        date_val = row.get('transaction date')
                        txn_date = self.parse_date(date_val)
                        if not txn_date: continue

                        amount = self.clean_decimal(row.get('amount'))
                        units = self.clean_decimal(row.get('units'))

                        # Type: Use SubTranType (e.g. RED, SIN) or Transaction Type (Redemption)
                        txn_type_code = str(row.get('transaction type', '')).strip()
                        txn_type = str(row.get('transaction description', '')).strip()

                        # Determine NAV
                        nav = None
                        raw_price = row.get('price') or row.get('nav')
                        if not pd.isna(raw_price):
                            nav = self.clean_decimal(raw_price)

                        # Fallback to calculation
                        if (nav is None or nav == 0) and units != 0:
                            nav = abs(amount) / abs(units)

                        # Fingerprint
                        # Use deterministic, source-aware fingerprint-based deduplication
                        row_dict = {
                            'folio number': str(row.get('folio number', '')).strip(),
                            'scheme code': scheme_code,
                            'transaction type': str(row.get('transaction type', '')).strip(),
                            'transaction description': str(row.get('transaction description', '')).strip(),
                            'amount': amount,
                            'units': units,
                            'transaction date': txn_date,
                            'transaction number': str(row.get('transaction number', '')).strip(),
                            'purchase transaction no': str(row.get('purchase transaction no', '')).strip(),
                            'siptrxnno': str(row.get('siptrxnno', '')).strip() if pd.notna(row.get('siptrxnno')) else None,
                            'trxn_suffix': str(row.get('trxn_suffix', '')).strip() if pd.notna(row.get('trxn_suffix')) else None,
                            'scan_ref_no': str(row.get('scan_ref_no', '')).strip() if pd.notna(row.get('scan_ref_no')) else None,
                            'reversal_code': str(row.get('reversal_code', '')).strip() if pd.notna(row.get('reversal_code')) else None,
                        }
                        fingerprint = generate_karvy_fingerprint(row_dict)

                        txn_nature = str(row.get('transaction description', '')).strip()
                        description = str(row.get('remarks', '')).strip()
                        tr_flag = str(row.get('transaction flag', '')).strip()

                        broker_code = str(row.get('agent code', '')).strip() or None
                        sub_broker_code = str(row.get('sub-broker code', '')).strip() or None
                        euin = str(row.get('euin', '')).strip() or None

                        stt = self.clean_decimal(row.get('stt'))
                        stamp_duty = self.clean_decimal(row.get('stamp duty charges'))

                        ihno = str(row.get('ihno', '')).strip() or str(row.get('instrument number', '')).strip() or None
                        ih_dt_val = row.get('instrument date')
                        ih_dt = self.parse_date(ih_dt_val) if ih_dt_val else None

                        bank_name = str(row.get('instrument bank', '')).strip() or None
                        load_amount = self.clean_decimal(row.get('load amount'))
                        tax_amount = self.clean_decimal(row.get('tdsamount'))

                        remarks = str(row.get('remarks', '')).strip() or None
                        location = str(row.get('branch name', '')).strip() or None

                        raw_row_data = {k: str(v) if pd.notna(v) else None for k, v in row.items()}

                        parsed_type, parsed_action = get_karvy_transaction_type_and_action(txn_type_code, description)

                        self.match_or_create_transaction(
                            investor, scheme, folio_number, fingerprint, txn_date, amount, units, txn_type_code, 'KARVY',
                            description=description, tr_flag=tr_flag, txn_number=txn_number, nav=nav,
                            raw_data=raw_row_data,
                            parsed_txn_type=txn_type if txn_type else parsed_type,
                            parsed_txn_action=parsed_action,
                            broker_code=broker_code, sub_broker_code=sub_broker_code, euin=euin,
                            stt=stt, stamp_duty=stamp_duty,
                            instrument_no=ihno, instrument_date=ih_dt, bank_name=bank_name,
                            load_amount=load_amount, tax_amount=tax_amount,
                            remarks=remarks, location=location, txn_nature=txn_nature
                        )

                except Exception as e:
                    logger.error(f"Error processing Karvy CSV row: {e}")
                    row_dict = row.to_dict()
                    row_dict['error'] = str(e)
                    self.failed_rows.append(row_dict)

            self.process_impacted_holdings()

            if self.rta_file and not self.is_retry:
                if self.failed_rows:
                     self.save_error_file()

                self.rta_file.status = RTAFile.STATUS_PROCESSED
                self.rta_file.processed_at = timezone.now()
                self.rta_file.save()
        except Exception as e:
            if self.rta_file and not self.is_retry:
                self.rta_file.status = RTAFile.STATUS_FAILED
                self.rta_file.error_log = str(e)
                self.rta_file.save()
            logger.error(f"Karvy CSV Parsing failed: {e}")
            if not getattr(self, 'is_retry', False) and not self.rta_file:
                raise e
