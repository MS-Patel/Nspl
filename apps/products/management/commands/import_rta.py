import csv
from django.core.management.base import BaseCommand
from apps.products.models import RTASchemeMapping, UnmatchedSchemeLog
from apps.products.matching import SchemeRecord, match_scheme


class Command(BaseCommand):
    help = 'Imports RTA scheme mapping data from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('path_to_csv', type=str, help='Path to the RTA CSV file')

    def handle(self, *args, **kwargs):
        file_path = kwargs['path_to_csv']

        try:
            with open(file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                # Assume columns like:
                # RTA Code, RTA Scheme Name, ISIN

                for row in reader:
                    rta_code = row.get('RTA Code')
                    rta_name = row.get('RTA Scheme Name')
                    isin = row.get('ISIN')

                    if not rta_code or not rta_name:
                        UnmatchedSchemeLog.objects.create(
                            source="RTA",
                            raw_data=row,
                            reason="Missing required fields (RTA Code or RTA Scheme Name)"
                        )
                        continue

                    record = SchemeRecord(name=rta_name, isin=isin)
                    scheme = match_scheme(record)

                    if not scheme:
                        UnmatchedSchemeLog.objects.create(
                            source="RTA",
                            raw_data=row,
                            reason=f"No matching Scheme found for ISIN: {isin} or Name: {rta_name}"
                        )
                        continue

                    # Create or update mapping
                    RTASchemeMapping.objects.update_or_create(
                        rta_code=rta_code,
                        defaults={
                            'scheme': scheme,
                            'rta_name': rta_name
                        }
                    )

            self.stdout.write(self.style.SUCCESS('Successfully processed RTA file.'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error processing file: {str(e)}'))
