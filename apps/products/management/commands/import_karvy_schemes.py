from django.core.management.base import BaseCommand
import pandas as pd
from apps.products.models import Scheme, AMC, SchemeCategory
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Imports Karvy Scheme Master (XLS) to map/create schemes. Matches against BSE schemes using Channel Partner Code.'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the Karvy scheme master XLS file')

    def handle(self, *args, **options):
        file_path = options['file_path']
        self.stdout.write(f"Processing Karvy Scheme Master from {file_path}...")

        try:
            # Read XLS
            df = pd.read_excel(file_path)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to read file: {e}"))
            return

        # Clean column names (strip spaces)
        df.columns = [str(c).strip() for c in df.columns]

        required_cols = ['Product Code', 'Fund Description']
        for col in required_cols:
            if col not in df.columns:
                 self.stdout.write(self.style.ERROR(f"Missing '{col}' column in XLS."))
                 return

        # Prepare stats
        total_rows = 0
        matched_bse = 0
        new_created = 0
        updated_count = 0

        # Load ALL schemes
        self.stdout.write("Loading all schemes from database...")
        all_schemes = list(Scheme.objects.all())

        # Map: channel_partner_code -> scheme (for matching BSE schemes)
        cp_map = {}
        # Map: scheme_code -> scheme (for existing Karvy-only schemes)
        scheme_code_map = {}

        for s in all_schemes:
            if s.channel_partner_code:
                cp_map[s.channel_partner_code] = s
            scheme_code_map[s.scheme_code] = s

        # Use a dict to store updates to avoid duplicates (keyed by scheme ID)
        updates_dict = {}
        # List for new creations
        schemes_to_create = []
        # Set to track scheme codes being created to avoid dupes in single run
        new_scheme_codes = set()

        # Get or Create generic AMC for unmapped schemes
        default_amc, _ = AMC.objects.get_or_create(code='KARVY_UNMAPPED', defaults={'name': 'Karvy Unmapped Schemes'})

        for index, row in df.iterrows():
            total_rows += 1
            product_code = str(row['Product Code']).strip()
            fund_desc = str(row['Fund Description']).strip()
            isin = str(row['ISIN']).strip()
            if isin.lower() == 'nan': isin = ''

            amfi = str(row['Amfi']).strip()
            if amfi.lower() == 'nan': amfi = ''

            # 1. Try to match existing BSE scheme by Channel Partner Code
            matched_scheme = cp_map.get(product_code)

            if matched_scheme:
                matched_bse += 1
                changed = False

                # Update RTA Scheme Code if missing or different (We prefer Karvy Product Code)
                if matched_scheme.rta_scheme_code != product_code:
                    matched_scheme.rta_scheme_code = product_code
                    changed = True

                # Update ISIN if missing in DB
                if not matched_scheme.isin and isin:
                    matched_scheme.isin = isin
                    changed = True

                # Update AMFI Code if missing
                if not matched_scheme.amfi_code and amfi:
                    matched_scheme.amfi_code = amfi
                    changed = True

                if changed:
                    updates_dict[matched_scheme.id] = matched_scheme

            else:
                # 2. No match -> Create/Update Karvy-only Scheme
                karvy_scheme_code = f"KARVY-{product_code}"

                if karvy_scheme_code in scheme_code_map:
                    # Update existing Karvy-only scheme
                    s = scheme_code_map[karvy_scheme_code]
                    changed = False

                    if s.name != fund_desc:
                        s.name = fund_desc
                        changed = True
                    if isin and s.isin != isin:
                        s.isin = isin
                        changed = True
                    if amfi and s.amfi_code != amfi:
                        s.amfi_code = amfi
                        changed = True

                    if changed:
                        updates_dict[s.id] = s

                elif karvy_scheme_code not in new_scheme_codes:
                    # Create new object
                    new_scheme = Scheme(
                        scheme_code=karvy_scheme_code,
                        name=fund_desc,
                        amc=default_amc,
                        category=None,
                        rta_scheme_code=product_code,
                        channel_partner_code=product_code,
                        isin=isin,
                        amfi_code=amfi if amfi else None,
                        rta_agent_code='KARVY',
                        # description=f"Imported from Karvy Master. Fund: {row.get('Fund')}, Plan: {row.get('Plan')}"
                    )
                    schemes_to_create.append(new_scheme)
                    new_scheme_codes.add(karvy_scheme_code)
                    new_created += 1

            if total_rows % 1000 == 0:
                self.stdout.write(f"Processed {total_rows} rows...")

        # Bulk Create
        if schemes_to_create:
            self.stdout.write(f"Creating {len(schemes_to_create)} new schemes...")
            Scheme.objects.bulk_create(schemes_to_create, batch_size=1000)

        # Bulk Update
        schemes_to_update = list(updates_dict.values())
        if schemes_to_update:
            self.stdout.write(f"Updating {len(schemes_to_update)} existing schemes...")
            # We explicitly list fields we might have touched
            Scheme.objects.bulk_update(schemes_to_update, ['rta_scheme_code', 'isin', 'amfi_code', 'name'], batch_size=1000)

        self.stdout.write(self.style.SUCCESS(f"Finished. Total Rows: {total_rows}, Matched BSE: {matched_bse}, New Created: {new_created}, Updated Existing: {len(schemes_to_update)}"))
