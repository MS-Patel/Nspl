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
from .models import RTAFile, Transaction, Holding
from apps.products.models import Scheme
from apps.users.models import InvestorProfile
from apps.investments.models import Folio
from apps.reconciliation.utils.reconcile import recalculate_holding

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

    def parse(self):
        raise NotImplementedError

    def save_error_file(self):
        """
        Generates an Excel file from failed rows and saves it to the RTAFile model.
        """
        if not self.failed_rows or not self.rta_file:
            return

        try:
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
        if not date_str:
            return None
        # Handle Pandas timestamp
        if isinstance(date_str, (pd.Timestamp, datetime)):
            return date_str.date()

        date_str = str(date_str).strip()
        formats = ["%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]
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

    def generate_fingerprint(self, values):
        """
        Generates a unique hash based on a list of row values.
        Used to uniquely identify rows even if they share the same Transaction No.
        """
        raw_str = "|".join([str(v).strip().upper() if v is not None else "" for v in values])
        return hashlib.md5(raw_str.encode('utf-8')).hexdigest()

    def get_or_create_folio(self, investor, scheme, folio_number):
        if investor and scheme and folio_number:
            Folio.objects.get_or_create(
                investor=investor,
                amc=scheme.amc,
                folio_number=folio_number
            )

    def get_or_create_provisional_investor(self, pan, name=None, is_offline=True):
        """
        Finds an investor by PAN or creates a provisional one.
        """
        if not pan:
            return None
        pan = pan.upper().strip()
        try:
            return InvestorProfile.objects.get(pan=pan)
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

            return profile

    def get_scheme(self, scheme_code, isin=None):
        """
        Tries to find scheme by Code (BSE/RTA) or ISIN.
        """
        scheme = None
        if scheme_code:
            scheme_code = str(scheme_code).strip()
            scheme = Scheme.objects.filter(scheme_code=scheme_code).first()
            if not scheme:
                # Try RTA Scheme Code match if we had such field populated
                scheme = Scheme.objects.filter(channel_partner_code=scheme_code).first()

        if not scheme and isin:
            scheme = Scheme.objects.filter(isin=isin).first()

        return scheme

    def match_or_create_transaction(self, investor, scheme, folio_number, txn_number, date, amount, units, txn_type, rta_code, description="", tr_flag=""):
        """
        Matches incoming RTA transaction with existing (Provisional) BSE transaction,
        or creates a new one. Updates existing RTA transactions if changed.
        """
        if not txn_number:
            return

        # 1. Check strict duplicate (already processed RTA txn in previous run) or Update
        existing_txn = Transaction.objects.filter(txn_number=txn_number).first()
        if existing_txn:
            # Update fields
            existing_txn.date = date
            existing_txn.amount = amount
            existing_txn.units = units
            existing_txn.txn_type_code = txn_type
            existing_txn.rta_code = rta_code
            existing_txn.description = description
            existing_txn.tr_flag = tr_flag
            existing_txn.source = Transaction.SOURCE_RTA
            existing_txn.is_provisional = False
            if self.rta_file:
                existing_txn.source_file = self.rta_file

            # Optionally update relation if missing
            if not existing_txn.investor and investor:
                existing_txn.investor = investor
            if not existing_txn.scheme and scheme:
                existing_txn.scheme = scheme

            existing_txn.save()
            logger.info(f"Updated existing transaction {txn_number}")

            # Recalculate Holding
            recalculate_holding(investor, scheme, folio_number)
            return

        # 2. Try to find a Provisional Match
        # Strategy: Match on Investor + Scheme + Folio + Approx Date + Amount
        # (Since we don't have BSE Order ID reliably in RTA file without specific column knowledge)

        # Date window: +/- 5 days
        date_min = date - timedelta(days=5)
        date_max = date + timedelta(days=5)

        candidates = Transaction.objects.filter(
            investor=investor,
            scheme=scheme,
            folio_number=folio_number,
            is_provisional=True,
            amount=amount, # Exact amount match
            date__range=[date_min, date_max]
        )

        # Prioritize match
        matched_txn = candidates.first()

        if matched_txn:
            # Update Existing Provisional Transaction to Confirmed RTA Transaction
            matched_txn.txn_number = txn_number # Update to authoritative RTA ID
            matched_txn.rta_code = rta_code
            matched_txn.txn_type_code = txn_type
            matched_txn.description = description
            matched_txn.tr_flag = tr_flag
            matched_txn.date = date
            matched_txn.units = units
            matched_txn.source = Transaction.SOURCE_RTA
            matched_txn.is_provisional = False
            if self.rta_file:
                matched_txn.source_file = self.rta_file
            matched_txn.save()
            logger.info(f"Matched and confirmed provisional transaction {matched_txn.id} with RTA ID {txn_number}")

        else:
            # Create New Transaction
            Transaction.objects.create(
                investor=investor,
                scheme=scheme,
                folio_number=folio_number,
                rta_code=rta_code,
                txn_type_code=txn_type,
                txn_number=txn_number,
                date=date,
                amount=amount,
                units=units,
                description=description,
                tr_flag=tr_flag,
                source=Transaction.SOURCE_RTA,
                is_provisional=False,
                source_file=self.rta_file if self.rta_file else None
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


class CAMSParser(BaseParser):
    """
    Parses CAMS WBR9 (Transaction Feed) Format.
    Assumes pipe-separated (|).
    """

    def parse(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f, delimiter='|')

                for row in reader:
                    try:
                        with transaction.atomic():
                            # Basic validation
                            if not row or len(row) < 15:
                                continue
                            if row[0].startswith('HED') or row[0].startswith('TRL'):
                                continue

                            # Extract Data
                            # Map indices based on WBR9 / Standard CAMS Feed
                            # 0: AMC, 1: Folio, 3: Scheme Code, 4: Inv Name (Sometimes), 8: Type, 9: Txn No, 12: Units, 13: Amount, 15: Date, 18: PAN

                            # Validate PAN
                            pan = row[18].strip() if len(row) > 18 else None
                            if not pan:
                                continue

                            # Extract Name (Best Effort)
                            inv_name = row[4].strip() if len(row) > 4 else None

                            # Fetch or Create Investor
                            investor = self.get_or_create_provisional_investor(pan, inv_name, is_offline=True)

                            # Fetch Scheme
                            scheme_code = row[3].strip()
                            isin = row[20].strip() if len(row) > 20 else None # Try ISIN from col 20 (WBR9 standard vary)

                            scheme = self.get_scheme(scheme_code, isin)
                            if not scheme:
                                logger.warning(f"Scheme not found: Code={scheme_code}, ISIN={isin}")
                                self.failed_rows.append({
                                    'row_data': str(row),
                                    'error': f"Scheme not found: Code={scheme_code}, ISIN={isin}"
                                })
                                continue

                            folio_number = row[1].strip()
                            txn_number = row[9].strip()

                            txn_date = self.parse_date(row[15])
                            if not txn_date:
                                continue

                            amount = self.clean_decimal(row[13])
                            units = self.clean_decimal(row[12])
                            txn_type = row[8].strip().upper()

                            # Delegate to helper
                            self.match_or_create_transaction(
                                investor, scheme, folio_number, txn_number, txn_date, amount, units, txn_type, 'CAMS'
                            )
                    except Exception as e:
                        logger.error(f"Error processing row {row}: {e}")
                        self.failed_rows.append({
                            'row_data': str(row),
                            'error': str(e)
                        })

            self.process_impacted_holdings()

            if self.rta_file:
                if self.failed_rows:
                     self.save_error_file()

                self.rta_file.status = RTAFile.STATUS_PROCESSED
                self.rta_file.processed_at = timezone.now()
                self.rta_file.save()

        except Exception as e:
            if self.rta_file:
                self.rta_file.status = RTAFile.STATUS_FAILED
                self.rta_file.error_log = str(e)
                self.rta_file.save()
            logger.error(f"CAMS Parsing failed: {e}")
            if not self.rta_file:
                raise e

class CAMSXLSParser(BaseParser):
    """
    Parses CAMS WBR2 Excel Format.
    """
    def parse(self):
        try:
            df = pd.read_excel(self.file_path)
            # Normalize columns to lowercase
            df.columns = df.columns.str.lower()

            for _, row in df.iterrows():
                try:
                    with transaction.atomic():
                        pan = str(row.get('pan', '')).strip()
                        if not pan or pan.lower() == 'nan': continue

                        inv_name = str(row.get('inv_name', '')).strip()
                        investor = self.get_or_create_provisional_investor(pan, inv_name, is_offline=True)

                        scheme_code = str(row.get('prodcode', '')).strip()
                        # Fallback to scheme name if code fails? No, rely on mapping
                        scheme = self.get_scheme(scheme_code)
                        if not scheme:
                            logger.warning(f"Scheme not found for CAMS XLS: {scheme_code}")
                            row_dict = row.to_dict()
                            row_dict['error'] = f"Scheme not found: {scheme_code}"
                            self.failed_rows.append(row_dict)
                            continue

                        folio_number = str(row.get('folio_no', '')).strip()
                        original_txn_number = str(row.get('trxnno', '')).strip()

                        date_val = row.get('traddate')
                        txn_date = self.parse_date(date_val)
                        if not txn_date: continue

                        amount = self.clean_decimal(row.get('amount'))
                        units = self.clean_decimal(row.get('units'))
                        txn_type = str(row.get('trxntype', '')).strip()
                        txn_stat = str(row.get('trxnstat', '')).strip()
                        nav_date = str(row.get('postdate', '')).strip()

                        # Generate Row Fingerprint for Uniqueness
                        # Fields: FMCODE(prodcode), TD_ACNO(folio), TD_TRNO(trxnno), TD_PRDT(traddate),
                        # TD_UNITS, TD_AMT, TD_TRTYPE(trxntype), TRNSTAT, NAVDATE(postdate)
                        # We use available CAMS equivalents
                        fingerprint = self.generate_fingerprint([
                            scheme_code, folio_number, original_txn_number, str(txn_date),
                            units, amount, txn_type, txn_stat, nav_date
                        ])

                        # Use fingerprint as unique suffix
                        unique_txn_number = f"{original_txn_number}-{fingerprint}"

                        # New fields for Fuzzy Logic
                        description = str(row.get('trxn_nature', '')).strip()
                        tr_flag = str(row.get('trxn_type_flag', '')).strip()
                        # If not found under full names, try short codes seen in some files
                        if not tr_flag:
                             tr_flag = str(row.get('trflag', '')).strip()

                        self.match_or_create_transaction(
                            investor, scheme, folio_number, unique_txn_number, txn_date, amount, units, txn_type, 'CAMS',
                            description=description, tr_flag=tr_flag
                        )
                except Exception as e:
                    logger.error(f"Error processing CAMS XLS row: {e}")
                    row_dict = row.to_dict()
                    row_dict['error'] = str(e)
                    self.failed_rows.append(row_dict)

            self.process_impacted_holdings()

            if self.rta_file:
                if self.failed_rows:
                     self.save_error_file()

                self.rta_file.status = RTAFile.STATUS_PROCESSED
                self.rta_file.processed_at = timezone.now()
                self.rta_file.save()
        except Exception as e:
            if self.rta_file:
                self.rta_file.status = RTAFile.STATUS_FAILED
                self.rta_file.error_log = str(e)
                self.rta_file.save()
            logger.error(f"CAMS XLS Parsing failed: {e}")
            if not self.rta_file:
                raise e


class KarvyParser(BaseParser):
    """
    Parses Karvy/KFintech MFD Mailback Format.
    """

    def parse(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f, delimiter='|')

                for row in reader:
                    try:
                        with transaction.atomic():
                            # Skip short rows
                            if not row or len(row) < 10:
                                continue

                            # Heuristic to detect Header or Data
                            if "Header" in row[0] or "Product" in row[0]:
                                continue

                            # Assuming Standard Karvy/MFD Layout (Pipe):
                            # 0: AMC, 1: Scheme Code, 3: Folio, 4: Name?, 5: Type, 6: Trxn No, 7: Units, 8: Amount, 9: Date

                            pan = None
                            # Try to find PAN in likely columns (often 14, 15, 18, 19)
                            for idx in [14, 15, 18, 19, 20]:
                                if idx < len(row) and len(row[idx]) == 10 and row[idx].isalnum():
                                    pan = row[idx].strip()
                                    break

                            if not pan:
                                continue

                            inv_name = row[4].strip() if len(row) > 4 else None

                            investor = self.get_or_create_provisional_investor(pan, inv_name, is_offline=True)

                            scheme_code = row[1].strip()
                            isin = None
                            # Try to find ISIN (often col 21 or 22)
                            if len(row) > 21 and row[21].startswith('IN'):
                                isin = row[21].strip()

                            scheme = self.get_scheme(scheme_code, isin)
                            if not scheme:
                                logger.warning(f"Scheme not found: Code={scheme_code}, ISIN={isin}")
                                self.failed_rows.append({
                                    'row_data': str(row),
                                    'error': f"Scheme not found: Code={scheme_code}, ISIN={isin}"
                                })
                                continue

                            folio_number = row[3].strip()
                            txn_number = row[6].strip()

                            txn_date = self.parse_date(row[9])
                            amount = self.clean_decimal(row[8])
                            units = self.clean_decimal(row[7])
                            txn_type = row[5].strip().upper()

                            # Delegate to helper
                            self.match_or_create_transaction(
                                investor, scheme, folio_number, txn_number, txn_date if txn_date else timezone.now().date(),
                                amount, units, txn_type, 'KARVY'
                            )
                    except Exception as e:
                        logger.error(f"Error processing Karvy row: {e}")
                        self.failed_rows.append({
                            'row_data': str(row),
                            'error': str(e)
                        })

            self.process_impacted_holdings()

            if self.rta_file:
                if self.failed_rows:
                     self.save_error_file()

                self.rta_file.status = RTAFile.STATUS_PROCESSED
                self.rta_file.processed_at = timezone.now()
                self.rta_file.save()

        except Exception as e:
            if self.rta_file:
                self.rta_file.status = RTAFile.STATUS_FAILED
                self.rta_file.error_log = str(e)
                self.rta_file.save()
            logger.error(f"Karvy Parsing failed: {e}")
            if not self.rta_file:
                raise e

class KarvyXLSParser(BaseParser):
    """
    Parses Karvy MFSD201 Excel Format.
    """
    def parse(self):
        try:
            # Skip first row (TRANSACTION REPORT) if exists, check header=1
            # Based on inspection, header is at index 1
            df = pd.read_excel(self.file_path, header=1)
            # Normalize columns to lowercase
            df.columns = df.columns.str.lower()

            for _, row in df.iterrows():
                try:
                    with transaction.atomic():
                        # Use lowercase 'pan1'
                        pan = str(row.get('pan1', '')).strip()
                        if not pan or pan.lower() == 'nan': continue

                        inv_name = str(row.get('invname', '')).strip()
                        investor = self.get_or_create_provisional_investor(pan, inv_name, is_offline=True)

                        scheme_code = str(row.get('fmcode', '')).strip()
                        scheme = self.get_scheme(scheme_code)
                        if not scheme:
                            logger.warning(f"Scheme not found for Karvy XLS: {scheme_code}")
                            row_dict = row.to_dict()
                            row_dict['error'] = f"Scheme not found: {scheme_code}"
                            self.failed_rows.append(row_dict)
                            continue

                        folio_number = str(row.get('td_acno', '')).strip()
                        original_txn_number = str(row.get('td_trno', '')).strip()

                        # Try NAVDATE, fallback to TD_PRDT
                        # keys are lowercase now
                        date_val = row.get('navdate')
                        if pd.isna(date_val): date_val = row.get('td_prdt')
                        txn_date = self.parse_date(date_val)
                        if not txn_date: continue

                        amount = self.clean_decimal(row.get('td_amt'))
                        units = self.clean_decimal(row.get('td_units'))
                        txn_type = str(row.get('td_trtype', '')).strip()

                        # For Fingerprint
                        fund_desc = str(row.get('td_fund', '')).strip() # TD_FUND
                        prdt_date = str(row.get('td_prdt', '')).strip() # TD_PRDT
                        trn_stat = str(row.get('trnstat', '')).strip() # TRNSTAT
                        nav_date_raw = str(row.get('navdate', '')).strip() # NAVDATE

                        # Generate Row Fingerprint
                        # Fields: FMCODE, TD_ACNO, TD_FUND, TD_TRNO, TD_PRDT, TD_UNITS, TD_AMT, TD_TRTYPE, TRNSTAT, NAVDATE
                        fingerprint = self.generate_fingerprint([
                            scheme_code, folio_number, fund_desc, original_txn_number, prdt_date,
                            units, amount, txn_type, trn_stat, nav_date_raw
                        ])

                        unique_txn_number = f"{original_txn_number}-{fingerprint}"

                        # New fields for Fuzzy Logic
                        description = str(row.get('trdesc', '')).strip()
                        tr_flag = str(row.get('trflag', '')).strip()
                        # If not found, try alternative names
                        if not tr_flag:
                             tr_flag = str(row.get('trxn_type_flag', '')).strip()

                        self.match_or_create_transaction(
                            investor, scheme, folio_number, unique_txn_number, txn_date, amount, units, txn_type, 'KARVY',
                            description=description, tr_flag=tr_flag
                        )
                except Exception as e:
                    logger.error(f"Error processing Karvy XLS row: {e}")
                    row_dict = row.to_dict()
                    row_dict['error'] = str(e)
                    self.failed_rows.append(row_dict)

            self.process_impacted_holdings()

            if self.rta_file:
                if self.failed_rows:
                     self.save_error_file()

                self.rta_file.status = RTAFile.STATUS_PROCESSED
                self.rta_file.processed_at = timezone.now()
                self.rta_file.save()
        except Exception as e:
            if self.rta_file:
                self.rta_file.status = RTAFile.STATUS_FAILED
                self.rta_file.error_log = str(e)
                self.rta_file.save()
            logger.error(f"Karvy XLS Parsing failed: {e}")
            if not self.rta_file:
                raise e


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

                            self.match_or_create_transaction(
                                investor, scheme, folio_number, txn_number, txn_date if txn_date else timezone.now().date(),
                                amount, units, txn_type, 'FRANKLIN'
                            )
                    except Exception as e:
                        logger.error(f"Error processing Franklin row: {e}")
                        self.failed_rows.append({
                            'row_data': str(row),
                            'error': str(e)
                        })

            self.process_impacted_holdings()

            if self.rta_file:
                if self.failed_rows:
                     self.save_error_file()

                self.rta_file.status = RTAFile.STATUS_PROCESSED
                self.rta_file.processed_at = timezone.now()
                self.rta_file.save()

        except Exception as e:
            if self.rta_file:
                self.rta_file.status = RTAFile.STATUS_FAILED
                self.rta_file.error_log = str(e)
                self.rta_file.save()
            logger.error(f"Franklin Parsing failed: {e}")
            if not self.rta_file:
                raise e
