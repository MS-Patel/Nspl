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

        # Load ALL schemes
        self.stdout.write("Loading all schemes from database...")
        all_schemes = list(Scheme.objects.all())

        # Build maps
        isin_map = {s.isin: s for s in all_schemes if s.isin}

        # Map for name matching (normalized)
        # We store (name -> scheme)
        name_map = {}
        for s in all_schemes:
            if s.name:
                name_map[s.name] = s

        # List of names for fuzzy matching
        scheme_names = list(name_map.keys())

        # Map for uniqueness check: amfi_code -> scheme_id
        # Note: We prioritize existing assignments in DB
        amfi_code_map = {s.amfi_code: s.id for s in all_schemes if s.amfi_code}

        count = 0
        updated = 0
        matched_by_isin = 0
        matched_by_name_exact = 0
        matched_by_name_fuzzy = 0

        for index, row in df.iterrows():
            amfi_code = str(row['Code']).strip()
            if not amfi_code or amfi_code.lower() == 'nan':
                continue

            # 1. Try matching by ISIN
            isin1 = row.get('ISIN Div Payout/ ISIN Growth')
            isin2 = row.get('ISIN Div Reinvestment')

            scheme = None

            if isin1 and isinstance(isin1, str):
                isin1 = isin1.strip()
                if isin1 in isin_map:
                    scheme = isin_map[isin1]

            if not scheme and isin2 and isinstance(isin2, str):
                isin2 = isin2.strip()
                if isin2 in isin_map:
                    scheme = isin_map[isin2]

            if scheme:
                matched_by_isin += 1
            else:
                # 2. Try Name Matching
                # Candidate names from CSV
                csv_names = []
                if 'Scheme NAV Name' in df.columns and pd.notna(row['Scheme NAV Name']):
                    csv_names.append(str(row['Scheme NAV Name']).strip())
                if 'Scheme Name' in df.columns and pd.notna(row['Scheme Name']):
                    csv_names.append(str(row['Scheme Name']).strip())

                # 2a. Exact Match
                for name in csv_names:
                    # Try finding exact name in DB
                    if name in name_map:
                        scheme = name_map[name]
                        matched_by_name_exact += 1
                        break

                # 2b. Fuzzy Match
                if not scheme and csv_names:
                    # Use the first available name (NAV name usually better)
                    query_name = csv_names[0]

                    # Extract best match
                    best_match = process.extractOne(query_name, scheme_names, scorer=fuzz.token_sort_ratio)

                    if best_match:
                        match_name, score = best_match
                        if score >= fuzzy_threshold:
                            scheme = name_map[match_name]
                            matched_by_name_fuzzy += 1
                            # self.stdout.write(f"Fuzzy Match: '{query_name}' -> '{match_name}' (Score: {score})")

            if scheme:
                # Check uniqueness constraint
                if amfi_code in amfi_code_map:
                    existing_id = amfi_code_map[amfi_code]
                    if existing_id != scheme.id:
                        # AMFI code already assigned to another scheme.
                        continue

                if scheme.amfi_code != amfi_code:
                    scheme.amfi_code = amfi_code
                    schemes_to_update.append(scheme)

                    # Update map so we don't assign this code again in this loop
                    amfi_code_map[amfi_code] = scheme.id
                    updated += 1

            count += 1
            if count % 100 == 0:
                self.stdout.write(f"Processed {count} rows... (ISIN: {matched_by_isin}, Exact Name: {matched_by_name_exact}, Fuzzy: {matched_by_name_fuzzy})")

        if schemes_to_update:
            try:
                Scheme.objects.bulk_update(schemes_to_update, ['amfi_code'], batch_size=1000)
                self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated} schemes with AMFI Codes."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Bulk update failed: {e}"))
        else:
            self.stdout.write("No schemes matched or updated.")

        self.stdout.write(f"Final Stats: ISIN Matches: {matched_by_isin}, Exact Name Matches: {matched_by_name_exact}, Fuzzy Name Matches: {matched_by_name_fuzzy}")
