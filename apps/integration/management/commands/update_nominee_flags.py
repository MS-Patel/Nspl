from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.users.models import InvestorProfile
from apps.integration.bse_client import BSEStarMFClient
import time

class Command(BaseCommand):
    help = 'Bulk update nominee flags to "N" for investors with missing nominee details (email/mobile).'

    def handle(self, *args, **kwargs):
        self.stdout.write("Identifying investors with missing nominee details...")

        # Filter Logic:
        # 1. Has UCC Code (Existing on BSE)
        # 2. Nomination Option is 'Y' (Expects nominees)
        # 3. Has Nominees with missing Mobile OR Email

        investors = InvestorProfile.objects.filter(
            ucc_code__isnull=False
        ).exclude(
            ucc_code=''
        ).filter(
            nomination_opt='Y'
        ).filter(
            Q(nominees__mobile='') | Q(nominees__email='')
        ).distinct()

        total_count = investors.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("No investors found matching the criteria."))
            return

        self.stdout.write(f"Found {total_count} investors to update.")

        client = BSEStarMFClient()
        batch_size = 50

        # Fetch all eligible investors
        investor_list = list(investors)

        for i in range(0, total_count, batch_size):
            batch = investor_list[i:i + batch_size]
            self.stdout.write(f"Processing batch {i//batch_size + 1} ({len(batch)} investors)...")

            try:
                result = client.bulk_update_nominee_flags(batch)
                self.stdout.write(f"Batch result: {result}")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing batch: {str(e)}"))

            # Sleep to be gentle on the API
            time.sleep(1)

        self.stdout.write(self.style.SUCCESS("Update process completed."))
