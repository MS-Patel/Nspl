from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.reconciliation.models import RTAFile
import os
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Cleans up RTAFile records and their associated physical files older than a specified number of days.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7, help='Number of days after which RTA files should be deleted.')

    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)

        self.stdout.write(f"Finding RTAFile records older than {days} days...")

        old_files = RTAFile.objects.filter(uploaded_at__lt=cutoff_date)
        count = old_files.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No old RTA files found to clean up."))
            return

        for rta_file in old_files:
            try:
                # Delete physical file
                if rta_file.file:
                    rta_file.file.delete(save=False)

                # Delete error file if it exists
                if rta_file.error_file:
                    rta_file.error_file.delete(save=False)

                rta_file.delete()

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error deleting RTAFile {rta_file.id}: {e}"))
                logger.error(f"Error deleting RTAFile {rta_file.id}: {e}")

        self.stdout.write(self.style.SUCCESS(f"Successfully deleted {count} old RTA file records."))
