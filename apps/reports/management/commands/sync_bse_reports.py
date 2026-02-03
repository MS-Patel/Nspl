from django.core.management.base import BaseCommand
from apps.integration.sync_utils import sync_bse_daily_reports

class Command(BaseCommand):
    help = 'Synchronizes BSE Star MF reports (Order Status, Allotment, Redemption) to local database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=3,
            help='Number of past days to sync (default: 3)'
        )

    def handle(self, *args, **options):
        days = options['days']
        self.stdout.write(self.style.SUCCESS(f'Starting sync for last {days} days...'))

        try:
            sync_bse_daily_reports(days=days)
            self.stdout.write(self.style.SUCCESS('Successfully completed BSE report sync.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during sync: {e}'))
