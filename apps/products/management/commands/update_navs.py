from django.core.management.base import BaseCommand
from apps.products.utils.nav_fetcher import fetch_amfi_navs
import logging

class Command(BaseCommand):
    help = 'Fetches daily NAVs from AMFI and updates the database.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting NAV Update..."))
        try:
            success = fetch_amfi_navs()
            if success:
                self.stdout.write(self.style.SUCCESS("NAV Update Completed Successfully."))
            else:
                self.stdout.write(self.style.ERROR("NAV Update Failed. Check logs."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
