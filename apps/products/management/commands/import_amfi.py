import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from apps.products.models import Scheme, NAVHistory, UnmatchedSchemeLog
from apps.products.matching import normalize_name, SchemeRecord, match_scheme

class Command(BaseCommand):
    help = 'Imports AMFI scheme data from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('path_to_csv', type=str, help='Path to the AMFI CSV file')

    def handle(self, *args, **kwargs):
        file_path = kwargs['path_to_csv']

        nav_records_to_create = []
        batch_size = 5000
        total_created = 0

        try:
            with open(file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row in reader:
                    amfi_code = row.get('Scheme Code', '').strip() or None
                    isin = row.get('ISIN Div Payout/ISIN Growth') or row.get('ISIN')
                    name = row.get('Scheme Name')
                    nav_str = row.get('Net Asset Value')
                    date_str = row.get('Date')

                    if not name:
                        continue

                    name_upper = name.upper()
                    plan_type = "DIRECT" if "DIRECT" in name_upper else "REGULAR"
                    option = "IDCW" if "IDCW" in name_upper or "DIVIDEND" in name_upper else "GROWTH"

                    normalized_n = normalize_name(name)

                    scheme = Scheme.objects.filter(amfi_code=amfi_code).first() if amfi_code else None
                    if not scheme and isin:
                         scheme = Scheme.objects.filter(isin=isin, plan_type=plan_type, option=option).first()

                    if not scheme:
                        scheme = Scheme.objects.create(
                            name=name,
                            normalized_name=normalized_n,
                            amfi_code=amfi_code,
                            isin=isin or '',
                            plan_type=plan_type,
                            option=option,
                            is_active=True
                        )
                        self.stdout.write(self.style.SUCCESS(f'Created new scheme: {name}'))
                    else:
                        updated = False
                        if amfi_code and not scheme.amfi_code:
                            scheme.amfi_code = amfi_code
                            updated = True
                        if isin and not scheme.isin:
                            scheme.isin = isin
                            updated = True
                        if updated:
                            scheme.save()

                    try:
                        if nav_str and date_str:
                            try:
                                nav = Decimal(nav_str)
                                date = datetime.strptime(date_str, "%d-%b-%Y").date()
                            except ValueError:
                                try:
                                    date = datetime.strptime(date_str, "%d-%m-%Y").date()
                                except ValueError:
                                    date = datetime.strptime(date_str, "%Y-%m-%d").date()

                            nav_records_to_create.append(
                                NAVHistory(scheme=scheme, nav_date=date, net_asset_value=nav)
                            )

                            if len(nav_records_to_create) >= batch_size:
                                NAVHistory.objects.bulk_create(nav_records_to_create, batch_size=batch_size, ignore_conflicts=True)
                                total_created += len(nav_records_to_create)
                                nav_records_to_create.clear()

                    except (InvalidOperation, ValueError, TypeError) as e:
                        UnmatchedSchemeLog.objects.create(
                            source="AMFI",
                            raw_data=row,
                            reason=f"Failed to parse NAV or Date: {str(e)}"
                        )

            if nav_records_to_create:
                NAVHistory.objects.bulk_create(nav_records_to_create, batch_size=batch_size, ignore_conflicts=True)
                total_created += len(nav_records_to_create)

            self.stdout.write(self.style.SUCCESS(f'Successfully bulk inserted {total_created} NAV records.'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error processing file: {str(e)}'))
