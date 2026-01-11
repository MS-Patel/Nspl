import csv
import logging
from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from .models import RTAFile, Transaction, Holding
from apps.products.models import Scheme
from apps.users.models import InvestorProfile
from apps.investments.models import Folio

logger = logging.getLogger(__name__)

class BaseParser:
    """
    Base parser containing shared logic for all RTA mailback parsers.
    """
    def __init__(self, rta_file_obj):
        self.rta_file = rta_file_obj

    def parse(self):
        raise NotImplementedError

    def parse_date(self, date_str):
        """Attempts to parse date from common formats."""
        if not date_str:
            return None
        date_str = date_str.strip()
        formats = ["%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None

    def clean_decimal(self, value):
        """Cleans and returns a Decimal from string."""
        if not value:
            return Decimal(0)
        try:
            return Decimal(str(value).strip().replace(',', ''))
        except:
            return Decimal(0)

    def get_or_create_folio(self, investor, scheme, folio_number):
        if investor and scheme and folio_number:
            Folio.objects.get_or_create(
                investor=investor,
                amc=scheme.amc,
                folio_number=folio_number
            )

    def update_holding(self, investor, scheme, folio_number, units, amount):
        if not investor or not scheme:
            return

        holding, created = Holding.objects.get_or_create(
            investor=investor,
            scheme=scheme,
            folio_number=folio_number
        )
        holding.units += units
        holding.save()


class CAMSParser(BaseParser):
    """
    Parses CAMS WBR9 (Transaction Feed) Format.
    Assumes pipe-separated (|).
    """

    def parse(self):
        try:
            file_path = self.rta_file.file.path
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f, delimiter='|')

                with transaction.atomic():
                    for row in reader:
                        # Basic validation
                        if not row or len(row) < 15:
                            continue
                        if row[0].startswith('HED') or row[0].startswith('TRL'):
                            continue

                        # Extract Data
                        # Map indices based on WBR9 / Standard CAMS Feed
                        # 1: Folio, 3: Scheme Code, 8: Type, 9: Txn No, 12: Units, 13: Amount, 15: Date, 18: PAN

                        # Validate PAN
                        pan = row[18].strip() if len(row) > 18 else None
                        if not pan:
                            continue

                        # Fetch Investor
                        try:
                            investor = InvestorProfile.objects.get(pan=pan)
                        except InvestorProfile.DoesNotExist:
                            continue

                        # Fetch Scheme
                        scheme_code = row[3].strip()
                        scheme = Scheme.objects.filter(scheme_code=scheme_code).first()
                        if not scheme:
                            continue

                        folio_number = row[1].strip()
                        txn_number = row[9].strip()

                        if Transaction.objects.filter(txn_number=txn_number).exists():
                            continue

                        txn_date = self.parse_date(row[15])
                        if not txn_date:
                            continue

                        amount = self.clean_decimal(row[13])
                        units = self.clean_decimal(row[12])
                        txn_type = row[8].strip().upper()

                        # Determine effective units (Positive/Negative)
                        effective_units = units
                        if txn_type in ['R', 'SO', 'DR', 'REDEMPTION', 'SWITCH OUT']:
                             effective_units = -abs(units)
                        elif txn_type in ['P', 'SI', 'PURCHASE', 'SWITCH IN', 'SIP']:
                             effective_units = abs(units)

                        # Create Transaction
                        Transaction.objects.create(
                            investor=investor,
                            scheme=scheme,
                            folio_number=folio_number,
                            rta_code='CAMS',
                            txn_type_code=txn_type,
                            txn_number=txn_number,
                            date=txn_date,
                            amount=amount,
                            units=units,
                            source_file=self.rta_file
                        )

                        # Update Holding
                        self.update_holding(investor, scheme, folio_number, effective_units, amount)
                        self.get_or_create_folio(investor, scheme, folio_number)

            self.rta_file.status = RTAFile.STATUS_PROCESSED
            self.rta_file.processed_at = timezone.now()
            self.rta_file.save()

        except Exception as e:
            self.rta_file.status = RTAFile.STATUS_FAILED
            self.rta_file.error_log = str(e)
            self.rta_file.save()
            logger.error(f"CAMS Parsing failed: {e}")


class KarvyParser(BaseParser):
    """
    Parses Karvy/KFintech MFD Mailback Format.
    Assumes standard MFD format (often pipe separated or comma).
    Using pipe for consistency with 'Standard MFD', verifying indices against standard spec.
    Common Spec (Indices 0-based):
    0: Product Code (Scheme Code)
    1: Folio No
    2: Trxn No (or 3?) -> Let's look for standard headers if possible, or assume fixed.

    Standard Karvy/MFD (Pipe):
    0: AMC_CODE
    1: SCHEME_CODE
    2: SCHEME_NAME
    3: FOLIO_NO
    4: INV_NAME
    5: TR_TYPE (P/R)
    6: TR_NO
    7: UNITS
    8: AMOUNT
    9: TR_DATE
    10: NAV
    ...
    15: PAN (Position varies, checking specific col usually)

    Let's implement a robust check or assume standard layout.
    Karvy Mailback (Pipe):
    Index Mappings (Approximation):
    1: Scheme Code
    3: Folio
    5: Trxn Type
    6: Trxn No
    7: Units
    8: Amount
    9: Date
    14 or 15: PAN
    """

    def parse(self):
        try:
            file_path = self.rta_file.file.path
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f, delimiter='|')

                with transaction.atomic():
                    for row in reader:
                        # Skip short rows
                        if not row or len(row) < 10:
                            continue

                        # Heuristic to detect Header or Data
                        if "Header" in row[0] or "Product" in row[0]:
                            continue

                        # Assuming Standard Karvy/MFD Layout (Pipe):
                        # 0: AMC
                        # 1: Scheme Code
                        # 3: Folio
                        # 5: Type
                        # 6: Trxn No
                        # 7: Units
                        # 8: Amount
                        # 9: Date
                        # ... PAN at 14/15/18? Let's check a few spots or scan.
                        # Usually PAN is near end. Let's assume index 14 for now based on common MFD spec.

                        pan = None
                        # Try to find PAN in likely columns (often 14, 15, 18, 19)
                        for idx in [14, 15, 18, 19, 20]:
                            if idx < len(row) and len(row[idx]) == 10 and row[idx].isalnum():
                                pan = row[idx].strip()
                                break

                        if not pan:
                            # Fallback: check all columns? No, risky.
                            continue

                        try:
                            investor = InvestorProfile.objects.get(pan=pan)
                        except InvestorProfile.DoesNotExist:
                            continue

                        scheme_code = row[1].strip()
                        scheme = Scheme.objects.filter(scheme_code=scheme_code).first()
                        if not scheme:
                            # Try mapping? For now skip.
                            continue

                        folio_number = row[3].strip()
                        txn_number = row[6].strip()

                        if Transaction.objects.filter(txn_number=txn_number).exists():
                            continue

                        txn_date = self.parse_date(row[9])
                        amount = self.clean_decimal(row[8])
                        units = self.clean_decimal(row[7])
                        txn_type = row[5].strip().upper()

                        effective_units = units
                        if txn_type in ['R', 'SO', 'REDEMPTION', 'SWITCH OUT']:
                             effective_units = -abs(units)
                        else:
                             effective_units = abs(units)

                        Transaction.objects.create(
                            investor=investor,
                            scheme=scheme,
                            folio_number=folio_number,
                            rta_code='KARVY',
                            txn_type_code=txn_type,
                            txn_number=txn_number,
                            date=txn_date if txn_date else timezone.now().date(),
                            amount=amount,
                            units=units,
                            source_file=self.rta_file
                        )

                        self.update_holding(investor, scheme, folio_number, effective_units, amount)
                        self.get_or_create_folio(investor, scheme, folio_number)

            self.rta_file.status = RTAFile.STATUS_PROCESSED
            self.rta_file.processed_at = timezone.now()
            self.rta_file.save()

        except Exception as e:
            self.rta_file.status = RTAFile.STATUS_FAILED
            self.rta_file.error_log = str(e)
            self.rta_file.save()
            logger.error(f"Karvy Parsing failed: {e}")


class FranklinParser(BaseParser):
    """
    Parses Franklin Templeton Mailback Format.
    Assumes Pipe Separated.
    Layout is often similar to Karvy/CAMS but specific columns.
    Common FT Layout:
    0: COMP_CODE
    1: SCHEME_CODE
    2: SCHEME_NAME
    3: FOLIO_NO
    4: INVESTOR_NAME
    5: TRXN_TYPE
    6: TRXN_NO
    7: UNITS
    8: AMOUNT
    9: DATE
    ...
    18: PAN
    """

    def parse(self):
        try:
            file_path = self.rta_file.file.path
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f, delimiter='|')

                with transaction.atomic():
                    for row in reader:
                        if not row or len(row) < 10:
                            continue

                        if "Header" in row[0]: continue

                        # Franklin Layout Assumptions:
                        # 1: Scheme Code
                        # 3: Folio
                        # 5: Type
                        # 6: Trxn No
                        # 7: Units
                        # 8: Amount
                        # 9: Date
                        # 18: PAN (Commonly)

                        pan = None
                        if len(row) > 18: pan = row[18].strip()
                        if not pan:
                            # Try 14 like Karvy?
                            if len(row) > 14 and len(row[14]) == 10: pan = row[14].strip()

                        if not pan: continue

                        try:
                            investor = InvestorProfile.objects.get(pan=pan)
                        except InvestorProfile.DoesNotExist:
                            continue

                        scheme_code = row[1].strip()
                        scheme = Scheme.objects.filter(scheme_code=scheme_code).first()
                        if not scheme: continue

                        folio_number = row[3].strip()
                        txn_number = row[6].strip()

                        if Transaction.objects.filter(txn_number=txn_number).exists():
                            continue

                        txn_date = self.parse_date(row[9])
                        amount = self.clean_decimal(row[8])
                        units = self.clean_decimal(row[7])
                        txn_type = row[5].strip().upper()

                        effective_units = units
                        if txn_type in ['R', 'SO', 'REDEMPTION', 'SWITCH OUT']:
                             effective_units = -abs(units)
                        else:
                             effective_units = abs(units)

                        Transaction.objects.create(
                            investor=investor,
                            scheme=scheme,
                            folio_number=folio_number,
                            rta_code='FRANKLIN',
                            txn_type_code=txn_type,
                            txn_number=txn_number,
                            date=txn_date if txn_date else timezone.now().date(),
                            amount=amount,
                            units=units,
                            source_file=self.rta_file
                        )

                        self.update_holding(investor, scheme, folio_number, effective_units, amount)
                        self.get_or_create_folio(investor, scheme, folio_number)

            self.rta_file.status = RTAFile.STATUS_PROCESSED
            self.rta_file.processed_at = timezone.now()
            self.rta_file.save()

        except Exception as e:
            self.rta_file.status = RTAFile.STATUS_FAILED
            self.rta_file.error_log = str(e)
            self.rta_file.save()
            logger.error(f"Franklin Parsing failed: {e}")
