from django.core.management.base import BaseCommand
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs all daily maintenance jobs: RTA Import, NAV Fetch, Holding Valuation, BSE Sync.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Daily Jobs..."))

        try:
            # 0. Fetch RTA Emails
            self.stdout.write("Step 0: Fetching RTA Emails...")
            call_command('fetch_rta_emails')

            # 1. Fetch Latest NAVs
            self.stdout.write("Step 1: Fetching NAVs...")
            call_command('update_navs')
            self.stdout.write("Step 1a: Fetching BSE NAVs...")
            call_command('update_bse_navs')

            # 2. Update Holding Valuations (Requires Latest NAVs)
            self.stdout.write("Step 2: Updating Holding Valuations...")
            call_command('update_holding_values')

            # 3. Sync BSE Reports (Orders, Allotments)
            self.stdout.write("Step 3: Syncing BSE Reports...")
            # Assuming 'sync_bse_reports' is the command name.
            # I checked previously and it was in apps/reports/management/commands/sync_bse_reports.py
            call_command('sync_bse_reports', days=1)

            self.stdout.write(self.style.SUCCESS("Daily Jobs Completed Successfully."))

        except Exception as e:
            logger.error(f"Daily Jobs Failed: {e}")
            self.stdout.write(self.style.ERROR(f"Daily Jobs Failed: {e}"))
