from django.core.management.base import BaseCommand
import pandas as pd
from apps.products.models import Scheme
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Imports AMFI Scheme Master CSV to map AMFI Codes to Schemes based on ISIN'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the AMFI scheme master CSV file')

    def handle(self, *args, **options):
        file_path = options['file_path']
        self.stdout.write(f"Processing AMFI Scheme Master from {file_path}...")

        try:
            # Read CSV - pandas handles various delimiters if specified, but default is comma
            # Based on user input, it seems to be tab or similar, but standard CSV is comma.
            # We'll assume standard CSV or try to infer.
            # Using 'on_bad_lines' to skip problematic rows if any.
            df = pd.read_csv(file_path, on_bad_lines='skip', dtype=str)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to read file: {e}"))
            return

        # Clean column names
        df.columns = [c.strip() for c in df.columns]

        # Check required columns
        # Based on user input: 'Code', 'ISIN Div Payout/ ISIN Growth', 'ISIN Div Reinvestment'
        required_cols = ['Code']
        possible_isin_cols = ['ISIN Div Payout/ ISIN Growth', 'ISIN Div Reinvestment']

        if 'Code' not in df.columns:
             self.stdout.write(self.style.ERROR("Missing 'Code' column in CSV."))
             return

        # Prepare bulk update list
        schemes_to_update = []

        # Cache existing schemes by ISIN for fast lookup
        # We only care about schemes that have an ISIN
        existing_schemes = Scheme.objects.exclude(isin__isnull=True).exclude(isin__exact='')
        isin_map = {s.isin: s for s in existing_schemes}

        count = 0
        updated = 0

        for index, row in df.iterrows():
            amfi_code = str(row['Code']).strip()
            if not amfi_code or amfi_code.lower() == 'nan':
                continue

            # Check Growth ISIN
            isin1 = row.get('ISIN Div Payout/ ISIN Growth')
            isin2 = row.get('ISIN Div Reinvestment')

            scheme = None

            # Try matching ISIN 1
            if isin1 and isinstance(isin1, str):
                isin1 = isin1.strip()
                if isin1 in isin_map:
                    scheme = isin_map[isin1]

            # Try matching ISIN 2 if not found
            if not scheme and isin2 and isinstance(isin2, str):
                isin2 = isin2.strip()
                if isin2 in isin_map:
                    scheme = isin_map[isin2]

            if scheme:
                if scheme.amfi_code != amfi_code:
                    scheme.amfi_code = amfi_code
                    schemes_to_update.append(scheme)
                    updated += 1

            count += 1
            if count % 1000 == 0:
                self.stdout.write(f"Processed {count} rows...")

        if schemes_to_update:
            Scheme.objects.bulk_update(schemes_to_update, ['amfi_code'], batch_size=1000)
            self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated} schemes with AMFI Codes."))
        else:
            self.stdout.write("No schemes matched or updated.")
