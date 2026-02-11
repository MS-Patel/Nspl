from django.core.management.base import BaseCommand
from datetime import datetime, date
from apps.products.utils.bse_nav_fetcher import fetch_bse_navs
import logging

class Command(BaseCommand):
    help = 'Fetches daily NAVs from BSE Star MF and updates the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date to fetch NAVs for (YYYY-MM-DD). Defaults to today.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting BSE NAV Update..."))

        target_date = date.today()
        if options['date']:
            try:
                target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(self.style.ERROR("Invalid date format. Use YYYY-MM-DD."))
                return

        try:
            success = fetch_bse_navs(target_date)
            if success:
                self.stdout.write(self.style.SUCCESS(f"BSE NAV Update Completed Successfully for {target_date}."))
            else:
                self.stdout.write(self.style.ERROR(f"BSE NAV Update Failed for {target_date}. Check logs."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
