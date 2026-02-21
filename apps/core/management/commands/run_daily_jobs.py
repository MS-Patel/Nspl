from django.core.management.base import BaseCommand
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs all daily maintenance jobs: RTA Import, NAV Fetch, Holding Valuation, BSE Sync.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Daily Jobs..."))

        try:
            # 1. Sync BSE Reports (Orders, Allotments) - Get Provisional Data First
            self.stdout.write("Step 1: Syncing BSE Reports...")
            call_command('sync_bse_reports', days=1)

            # 2. Fetch RTA Emails - Confirm Transactions (Matches Provisional)
            self.stdout.write("Step 2: Fetching RTA Emails...")
            call_command('fetch_rta_emails')

            # 3. Fetch Latest NAVs
            self.stdout.write("Step 3: Fetching NAVs...")
            call_command('update_navs')
            self.stdout.write("Step 3a: Fetching BSE NAVs...")
            call_command('update_bse_navs')

            # 4. Update Holding Valuations (Requires Latest Units from Steps 1/2 and NAVs from Step 3)
            self.stdout.write("Step 4: Updating Holding Valuations...")
            call_command('update_holding_values')

            self.stdout.write(self.style.SUCCESS("Daily Jobs Completed Successfully."))

        except Exception as e:
            logger.error(f"Daily Jobs Failed: {e}")
            self.stdout.write(self.style.ERROR(f"Daily Jobs Failed: {e}"))
