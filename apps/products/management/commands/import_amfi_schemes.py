from django.core.management.base import BaseCommand
import pandas as pd
from apps.products.models import Scheme
import logging
from thefuzz import process, fuzz

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Imports AMFI Scheme Master CSV to map AMFI Codes to Schemes based on ISIN and Name fuzzy matching'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the AMFI scheme master CSV file')
        parser.add_argument('--fuzzy-threshold', type=int, default=85, help='Threshold score for fuzzy name matching (0-100)')

    def handle(self, *args, **options):
        file_path = options['file_path']
        fuzzy_threshold = options['fuzzy_threshold']
        self.stdout.write(f"Processing AMFI Scheme Master from {file_path} with fuzzy threshold {fuzzy_threshold}...")

        try:
            # Read CSV
            df = pd.read_csv(file_path, on_bad_lines='skip', dtype=str)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to read file: {e}"))
            return

        # Clean column names
        df.columns = [c.strip() for c in df.columns]

        if 'Code' not in df.columns:
             self.stdout.write(self.style.ERROR("Missing 'Code' column in CSV."))
             return

        # Prepare bulk update list
        schemes_to_update = []
        # Track updated IDs to avoid adding same scheme multiple times in one run if CSV has dupes
        updated_scheme_ids = set()

        # Load ALL schemes
        self.stdout.write("Loading all schemes from database...")
        all_schemes = list(Scheme.objects.all())

        # Build maps
        isin_map = {s.isin: s for s in all_schemes if s.isin}

        # Map for name matching (normalized)
        name_map = {}
        for s in all_schemes:
            if s.name:
                name_map[s.name] = s

        # List of names for fuzzy matching
        scheme_names = list(name_map.keys())

        count = 0
        updated = 0
        matched_by_isin = 0
        matched_by_name_exact = 0
        matched_by_name_fuzzy = 0

        for index, row in df.iterrows():
            amfi_code = str(row['Code']).strip()
            if not amfi_code or amfi_code.lower() == 'nan':
                continue

            # Identify schemes for this AMFI Code
            matched_schemes_for_row = []

            # 1. Try matching by ISIN 1
            isin1 = row.get('ISIN Div Payout/ ISIN Growth')
            if isin1 and isinstance(isin1, str):
                isin1 = isin1.strip()
                if isin1 in isin_map:
                    matched_schemes_for_row.append(isin_map[isin1])

            # 2. Try matching by ISIN 2
            isin2 = row.get('ISIN Div Reinvestment')
            if isin2 and isinstance(isin2, str):
                isin2 = isin2.strip()
                if isin2 in isin_map:
                    matched_schemes_for_row.append(isin_map[isin2])

            if matched_schemes_for_row:
                matched_by_isin += len(matched_schemes_for_row)
            else:
                # 3. Fallback: Name Matching (only if no ISIN match found)
                scheme = None

                csv_names = []
                if 'Scheme NAV Name' in df.columns and pd.notna(row['Scheme NAV Name']):
                    csv_names.append(str(row['Scheme NAV Name']).strip())
                if 'Scheme Name' in df.columns and pd.notna(row['Scheme Name']):
                    csv_names.append(str(row['Scheme Name']).strip())

                # 3a. Exact Match
                for name in csv_names:
                    if name in name_map:
                        scheme = name_map[name]
                        matched_by_name_exact += 1
                        break

                # 3b. Fuzzy Match
                if not scheme and csv_names:
                    query_name = csv_names[0]
                    best_match = process.extractOne(query_name, scheme_names, scorer=fuzz.token_sort_ratio)
                    if best_match:
                        match_name, score = best_match
                        if score >= fuzzy_threshold:
                            scheme = name_map[match_name]
                            matched_by_name_fuzzy += 1

                if scheme:
                    matched_schemes_for_row.append(scheme)

            # Assign AMFI Code to all matched schemes
            for scheme in matched_schemes_for_row:
                if scheme.amfi_code != amfi_code:
                    scheme.amfi_code = amfi_code

                    # Prevent duplicate updates in list
                    if scheme.id not in updated_scheme_ids:
                        schemes_to_update.append(scheme)
                        updated_scheme_ids.add(scheme.id)
                        updated += 1

            count += 1
            if count % 1000 == 0:
                self.stdout.write(f"Processed {count} rows... (Pending Updates: {updated})")

        if schemes_to_update:
            try:
                self.stdout.write(f"Committing updates for {len(schemes_to_update)} schemes...")
                Scheme.objects.bulk_update(schemes_to_update, ['amfi_code'], batch_size=1000)
                self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated} schemes with AMFI Codes."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Bulk update failed: {e}"))
        else:
            self.stdout.write("No schemes matched or updated.")

        self.stdout.write(f"Final Stats: Matched by ISIN: {matched_by_isin}, Exact Name: {matched_by_name_exact}, Fuzzy Name: {matched_by_name_fuzzy}")
