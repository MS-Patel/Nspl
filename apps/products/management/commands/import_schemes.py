
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
        if not amc_code:
             return

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

        # 3. Helpers
        def parse_bool(val):
            if not val: return False
            val = val.strip().upper()
            return val == 'Y' or val == '1'

        def parse_date(val):
            if not val: return None
            val = val.strip()
            if not val: return None
            try:
                # Format: Jul 19 2010
                return datetime.strptime(val, '%b %d %Y').date()
            except ValueError:
                return None

        def parse_time(val):
            if not val: return None
            val = val.strip()
            if not val: return None
            try:
                # Format: 14:30:00
                return datetime.strptime(val, '%H:%M:%S').time()
            except ValueError:
                return None

        def parse_decimal(val):
            if not val: return 0
            val = val.strip()
            if not val: return 0
            return val

        def parse_int(val):
            if not val: return None
            val = val.strip()
            if not val: return None
            try:
                return int(val)
            except ValueError:
                return None

        # 4. Extract Data
        unique_no = parse_int(row.get('Unique No'))
        scheme_code = row.get('Scheme Code')

        if not scheme_code:
             return

        scheme_data = {
            'amc': amc,
            'category': category,
            'name': row.get('Scheme Name'),
            'isin': row.get('ISIN') or '',
            'rta_scheme_code': row.get('RTA Scheme Code'),
            'amc_scheme_code': row.get('AMC Scheme Code'),
            'scheme_type': row.get('Scheme Type'),
            'scheme_plan': row.get('Scheme Plan'),

            'purchase_allowed': parse_bool(row.get('Purchase Allowed')),
            'purchase_transaction_mode': row.get('Purchase Transaction mode'),
            'min_purchase_amount': parse_decimal(row.get('Minimum Purchase Amount')),
            'additional_purchase_amount': parse_decimal(row.get('Additional Purchase Amount')),
            'max_purchase_amount': parse_decimal(row.get('Maximum Purchase Amount')),
            'purchase_amount_multiplier': parse_decimal(row.get('Purchase Amount Multiplier')),
            'purchase_cutoff_time': parse_time(row.get('Purchase Cutoff Time')),

            'redemption_allowed': parse_bool(row.get('Redemption Allowed')),
            'redemption_transaction_mode': row.get('Redemption Transaction Mode'),
            'min_redemption_qty': parse_decimal(row.get('Minimum Redemption Qty')),
            'redemption_qty_multiplier': parse_decimal(row.get('Redemption Qty Multiplier')),
            'max_redemption_qty': parse_decimal(row.get('Maximum Redemption Qty')),
            'min_redemption_amount': parse_decimal(row.get('Redemption Amount - Minimum')),
            'max_redemption_amount': parse_decimal(row.get('Redemption Amount – Maximum')),
            'redemption_amount_multiple': parse_decimal(row.get('Redemption Amount Multiple')),
            'redemption_cutoff_time': parse_time(row.get('Redemption Cut off Time')),

            'is_sip_allowed': parse_bool(row.get('SIP FLAG')),
            'is_stp_allowed': parse_bool(row.get('STP FLAG')),
            'is_swp_allowed': parse_bool(row.get('SWP Flag')),
            'is_switch_allowed': parse_bool(row.get('Switch FLAG')),

            'start_date': parse_date(row.get('Start Date')),
            'end_date': parse_date(row.get('End Date')),
            'reopening_date': parse_date(row.get('ReOpening Date')),

            'face_value': parse_decimal(row.get('Face Value') or '0'),
            'settlement_type': row.get('SETTLEMENT TYPE'),

            'unique_no': unique_no,
            'rta_agent_code': row.get('RTA Agent Code'),
            'amc_active_flag': parse_bool(row.get('AMC Active Flag')),
            'dividend_reinvestment_flag': parse_bool(row.get('Dividend Reinvestment Flag')),
            'amc_ind': row.get('AMC_IND'),
            'exit_load_flag': parse_bool(row.get('Exit Load Flag')),
            'exit_load': row.get('Exit Load'),
            'lock_in_period_flag': parse_bool(row.get('Lock-in Period Flag')),
            'lock_in_period': row.get('Lock-in Period'),
            'channel_partner_code': row.get('Channel Partner Code'),
        }

        # 5. Update or Create Logic
        scheme = None
        if unique_no:
            scheme = Scheme.objects.filter(unique_no=unique_no).first()

        if not scheme and scheme_code:
            scheme = Scheme.objects.filter(scheme_code=scheme_code).first()

        if scheme:
            # Update existing
            for key, value in scheme_data.items():
                setattr(scheme, key, value)
            scheme.save()
        else:
            # Create new
            Scheme.objects.create(scheme_code=scheme_code, **scheme_data)
