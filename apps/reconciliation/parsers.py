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
    def __init__(self, rta_file_obj):
        self.rta_file = rta_file_obj

    def parse(self):
        raise NotImplementedError

    def get_or_create_folio(self, investor, scheme, folio_number):
        # Helper to ensure Folio exists in Investments app too
        if investor and scheme and folio_number:
            Folio.objects.get_or_create(
                investor=investor,
                amc=scheme.amc,
                folio_number=folio_number
            )

    def update_holding(self, investor, scheme, folio_number, units, amount):
        """
        Updates the aggregate Holding model.
        Simple logic: Add units/amount.
        In reality, this needs to handle redemptions (subtracting) and FIFO for cost.
        For Phase 6 MVP, we'll do simple summation or just rely on the fact that
        WBR9 is transaction feed.

        Better approach: Recalculate holding from scratch for this folio?
        Or just increment.
        """
        if not investor or not scheme:
            return

        holding, created = Holding.objects.get_or_create(
            investor=investor,
            scheme=scheme,
            folio_number=folio_number
        )

        # Simple addition for MVP (Redemptions should have negative units in the parser)
        holding.units += units
        # Cost averaging is complex. For now, we add cost.
        # Ideally: new_avg = ((old_units * old_avg) + (new_units * new_price)) / total_units
        # But if units are negative (redemption), we reduce units but avg cost stays same?
        # Let's keep it simple: Just track units for now.

        holding.save()


class CAMSParser(BaseParser):
    """
    Parses CAMS WBR9 (Transaction Feed) Format.
    Format is typically Pipe Separated (|).
    Columns (Indices):
    0: AMC Code
    1: Folio No
    3: Scheme Code
    5: Investor Name
    8: Transaction Type (P/R/S)
    9: Transaction Number
    12: Units
    13: Amount
    15: Date (DD-MMM-YYYY or DD/MM/YYYY)
    18: PAN
    """

    def parse(self):
        try:
            file_path = self.rta_file.file.path
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # CAMS WBR9 often doesn't have headers, or skips first line.
                # We'll assume standard format.
                reader = csv.reader(f, delimiter='|')

                with transaction.atomic():
                    for row in reader:
                        if not row or len(row) < 15:
                            continue

                        # Basic mapping (Indices based on standard WBR9 spec - verify with real file later)
                        # Adjusting indices based on typical WBR2/WBR9
                        # 0: HED (Header) / DTL (Detail)
                        # If row starts with 'HED' or 'TRL', skip
                        if row[0].startswith('HED') or row[0].startswith('TRL'):
                            continue

                        # Extract fields
                        # Assuming DTL|AMC|FOLIO|...
                        # If file is raw WBR9, it might not have DTL prefix.
                        # Let's assume raw columns for now, based on typical experience.
                        # We will need to iterate and refine this with real data.

                        # Trying to find PAN to link Investor
                        pan = row[18].strip() if len(row) > 18 else None
                        if not pan:
                            continue

                        # Find Investor
                        investor = None
                        try:
                            investor = InvestorProfile.objects.get(pan=pan)
                        except InvestorProfile.DoesNotExist:
                            # Log warning or skip
                            # logger.warning(f"Investor not found for PAN: {pan}")
                            continue

                        # Find Scheme
                        # CAMS uses its own Scheme Codes. We need to map them to ISIN or our Scheme Code.
                        # row[3] is usually Product Code. row[4] ISIN?
                        # Let's assume row[3] matches our Scheme Code for now (Ideal world)
                        # Or we need a mapping table.
                        scheme_code = row[3].strip()
                        scheme = Scheme.objects.filter(scheme_code=scheme_code).first()

                        if not scheme:
                            # Try ISIN if available
                            # scheme = Scheme.objects.filter(isin=...).first()
                            continue

                        folio_number = row[1].strip()
                        txn_number = row[9].strip()

                        # Check duplicate
                        if Transaction.objects.filter(txn_number=txn_number).exists():
                            continue

                        # Parse Date
                        date_str = row[15].strip()
                        try:
                            txn_date = datetime.strptime(date_str, "%d-%b-%Y").date()
                        except ValueError:
                            try:
                                txn_date = datetime.strptime(date_str, "%d/%m/%Y").date()
                            except:
                                continue

                        # Amounts
                        try:
                            amount = Decimal(row[13].strip())
                            units = Decimal(row[12].strip())
                        except:
                            amount = Decimal(0)
                            units = Decimal(0)

                        txn_type = row[8].strip().upper()

                        # Handle Redemptions (Switch Out, Redemption) -> Negative Units
                        # CAMS types: P (Purchase), R (Redemption), SI (Switch In), SO (Switch Out)
                        # If the file provides positive numbers for Redemptions, we need to negate them for Holding calc.
                        # Usually WBR9 gives absolute values.

                        effective_units = units
                        if txn_type in ['R', 'SO', 'DR']: # DR = Debit?
                             effective_units = -abs(units)

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
                            units=units, # Store absolute value in Transaction usually, or signed?
                                         # Let's store absolute as per feed, logic handles sign in holding.
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
            logger.error(f"Parsing failed: {e}")
