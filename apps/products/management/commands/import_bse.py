import csv
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from apps.products.models import BSESchemeMapping, UnmatchedSchemeLog
from apps.products.matching import SchemeRecord, match_scheme


class Command(BaseCommand):
    help = 'Imports BSE scheme mapping data from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('path_to_csv', type=str, help='Path to the BSE CSV file')

    def handle(self, *args, **kwargs):
        file_path = kwargs['path_to_csv']

        try:
            with open(file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                # Assume columns like:
                # Scheme Code, ISIN, Scheme Name, Transaction Type, Minimum Amount, Maximum Amount

                for row in reader:
                    bse_code = row.get('Scheme Code')
                    isin = row.get('ISIN')
                    name = row.get('Scheme Name')
                    txn_type = row.get('Transaction Type')
                    min_amt_str = row.get('Minimum Amount')
                    max_amt_str = row.get('Maximum Amount')

                    if not name or not bse_code or not txn_type:
                        UnmatchedSchemeLog.objects.create(
                            source="BSE",
                            raw_data=row,
                            reason="Missing required fields (Scheme Code, Scheme Name, or Transaction Type)"
                        )
                        continue

                    # Validate Transaction Type
                    valid_txn_types = {"LUMPSUM", "SIP", "STP", "SWP"}
                    txn_type_upper = txn_type.upper()
                    if txn_type_upper not in valid_txn_types:
                        # try mapping if names differ
                        if "SIP" in txn_type_upper: txn_type_upper = "SIP"
                        elif "STP" in txn_type_upper: txn_type_upper = "STP"
                        elif "SWP" in txn_type_upper: txn_type_upper = "SWP"
                        else: txn_type_upper = "LUMPSUM"

                    record = SchemeRecord(name=name, isin=isin)
                    scheme = match_scheme(record)

                    if not scheme:
                        UnmatchedSchemeLog.objects.create(
                            source="BSE",
                            raw_data=row,
                            reason=f"No matching Scheme found for ISIN: {isin} or Name: {name}"
                        )
                        continue

                    min_amount = None
                    max_amount = None
                    try:
                        if min_amt_str:
                            min_amount = Decimal(min_amt_str)
                        if max_amt_str:
                            max_amount = Decimal(max_amt_str)
                    except (InvalidOperation, ValueError):
                        pass

                    # Create or update mapping
                    BSESchemeMapping.objects.update_or_create(
                        bse_code=bse_code,
                        defaults={
                            'scheme': scheme,
                            'transaction_type': txn_type_upper,
                            'min_amount': min_amount,
                            'max_amount': max_amount,
                            'is_active': True
                        }
                    )

            self.stdout.write(self.style.SUCCESS('Successfully processed BSE file.'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error processing file: {str(e)}'))
