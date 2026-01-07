
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.products.models import AMC, Scheme, SchemeCategory
from datetime import datetime
import csv
import os

class Command(BaseCommand):
    help = 'Import Scheme Master from a pipe-separated file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, nargs='?', help='Path to the scheme master file')

    def handle(self, *args, **options):
        file_path = options['file_path']

        # Default to the sample fixture if no file path provided
        if not file_path:
            file_path = os.path.join(settings.BASE_DIR, 'apps/products/fixtures/scheme_master_sample.txt')

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        self.stdout.write(f'Importing schemes from {file_path}...')

        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            # The file is pipe separated
            reader = csv.DictReader(f, delimiter='|')

            # Clean up headers (remove extra spaces if any)
            reader.fieldnames = [name.strip() for name in reader.fieldnames]

            for row in reader:
                try:
                    self.process_row(row)
                    count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing row {row.get('Scheme Code')}: {e}"))

        self.stdout.write(self.style.SUCCESS(f'Successfully imported/updated {count} schemes.'))

    def process_row(self, row):
        # 1. Get or Create AMC
        amc_code = row.get('AMC Code')
        # Simple name extraction from code for now, or use code as name if unknown
        amc_name = amc_code.replace('_MF', '').replace('_', ' ')
        amc, _ = AMC.objects.get_or_create(code=amc_code, defaults={'name': amc_name})

        # 2. Get or Create Category
        cat_code = row.get('Scheme Type')
        category = None
        if cat_code:
            category, _ = SchemeCategory.objects.get_or_create(
                code=cat_code,
                defaults={'name': cat_code}
            )

        # 3. Parse Booleans
        def parse_bool(val):
            return val.strip().upper() == 'Y'

        # 4. Parse Dates
        def parse_date(val):
            val = val.strip()
            if not val:
                return None
            try:
                # Format: Jul 19 2010
                return datetime.strptime(val, '%b %d %Y').date()
            except ValueError:
                return None

        # 5. Parse Decimals (handle empty strings)
        def parse_decimal(val):
            val = val.strip()
            if not val:
                return 0
            return val

        # 6. Create/Update Scheme
        scheme_code = row.get('Scheme Code')
        isin = row.get('ISIN')

        scheme_data = {
            'amc': amc,
            'category': category,
            'name': row.get('Scheme Name'),
            'isin': isin,
            'rta_scheme_code': row.get('RTA Scheme Code'),
            'scheme_type': row.get('Scheme Type'),
            'scheme_plan': row.get('Scheme Plan'),

            'purchase_allowed': parse_bool(row.get('Purchase Allowed')),
            'min_purchase_amount': parse_decimal(row.get('Minimum Purchase Amount')),
            'max_purchase_amount': parse_decimal(row.get('Maximum Purchase Amount')),
            'purchase_amount_multiplier': parse_decimal(row.get('Purchase Amount Multiplier')),

            'redemption_allowed': parse_bool(row.get('Redemption Allowed')),
            'min_redemption_qty': parse_decimal(row.get('Minimum Redemption Qty')),
            'min_redemption_amount': parse_decimal(row.get('Redemption Amount - Minimum')),

            'is_sip_allowed': parse_bool(row.get('SIP FLAG')),
            'is_stp_allowed': parse_bool(row.get('STP FLAG')),
            'is_swp_allowed': parse_bool(row.get('SWP Flag')),
            'is_switch_allowed': parse_bool(row.get('Switch FLAG')),

            'start_date': parse_date(row.get('Start Date')),
            'end_date': parse_date(row.get('End Date')),
            'reopening_date': parse_date(row.get('ReOpening Date')),

            'face_value': parse_decimal(row.get('Face Value') or '0'),
            'settlement_type': row.get('SETTLEMENT TYPE'),
        }

        Scheme.objects.update_or_create(
            scheme_code=scheme_code,
            defaults=scheme_data
        )
