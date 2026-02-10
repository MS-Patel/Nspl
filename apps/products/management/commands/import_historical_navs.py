from django.core.management.base import BaseCommand
import requests
import pandas as pd
from decimal import Decimal
from datetime import datetime
from apps.products.models import Scheme, NAVHistory

class Command(BaseCommand):
    help = 'Imports historical NAV data for schemes with a valid AMFI Code using the mfapi.in API.'

    def handle(self, *args, **options):
        # 1. Identify Target Schemes
        # We only want schemes that have an AMFI Code but might be missing history.
        # For now, let's target all schemes with an AMFI code.
        schemes = Scheme.objects.exclude(amfi_code__isnull=True).exclude(amfi_code='')

        total_schemes = schemes.count()
        self.stdout.write(f"Found {total_schemes} schemes with AMFI Codes.")

        if total_schemes == 0:
            self.stdout.write(self.style.WARNING("No schemes with AMFI codes found. Please run 'import_amfi_schemes' first."))
            return

        for i, scheme in enumerate(schemes, 1):
            amfi_code = scheme.amfi_code
            self.stdout.write(f"[{i}/{total_schemes}] Fetching history for {scheme.name} (AMFI: {amfi_code})...")

            try:
                # 2. Fetch Data from API
                url = f"https://api.mfapi.in/mf/{amfi_code}"
                response = requests.get(url, timeout=10)

                if response.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"  Failed to fetch data for {amfi_code}. Status: {response.status_code}"))
                    continue

                data = response.json()
                nav_list = data.get('data', [])

                if not nav_list:
                    self.stdout.write(self.style.WARNING(f"  No NAV history found for {amfi_code}."))
                    continue

                # 3. Prepare Bulk Create/Update
                # We need to check which dates already exist to avoid duplicates or updates if not needed.
                # Since we want to fill gaps, let's fetch existing dates.
                existing_dates = set(
                    NAVHistory.objects.filter(scheme=scheme).values_list('nav_date', flat=True)
                )

                new_navs = []

                for entry in nav_list:
                    date_str = entry.get('date') # Format: dd-mm-yyyy
                    nav_str = entry.get('nav')

                    if not date_str or not nav_str:
                        continue

                    try:
                        nav_date = datetime.strptime(date_str, '%d-%m-%Y').date()

                        # Skip if already exists
                        if nav_date in existing_dates:
                            continue

                        nav_val = Decimal(nav_str)

                        new_navs.append(NAVHistory(
                            scheme=scheme,
                            nav_date=nav_date,
                            net_asset_value=nav_val
                        ))
                    except (ValueError, TypeError) as e:
                        # self.stdout.write(self.style.WARNING(f"  Skipping invalid entry: {entry} - {e}"))
                        continue

                # 4. Save to DB
                if new_navs:
                    NAVHistory.objects.bulk_create(new_navs, batch_size=1000)
                    self.stdout.write(self.style.SUCCESS(f"  Imported {len(new_navs)} new NAV records."))
                else:
                    self.stdout.write(f"  Up to date.")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error processing {scheme.name}: {e}"))

        self.stdout.write(self.style.SUCCESS("Historical NAV import completed."))
