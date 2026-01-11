from django.core.management.base import BaseCommand
from apps.products.utils.nav_fetcher import fetch_amfi_navs

class Command(BaseCommand):
    help = 'Fetches daily NAVs from AMFI'

    def handle(self, *args, **options):
        self.stdout.write("Fetching NAVs from AMFI...")
        success = fetch_amfi_navs()
        if success:
            self.stdout.write(self.style.SUCCESS("Successfully fetched and updated NAVs."))
        else:
            self.stdout.write(self.style.ERROR("Failed to fetch NAVs."))
