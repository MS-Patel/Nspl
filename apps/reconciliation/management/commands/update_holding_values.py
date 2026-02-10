import logging
from django.core.management.base import BaseCommand
from django.db.models import F, Subquery, OuterRef
from django.utils import timezone
from apps.products.models import Scheme, NAVHistory
from apps.reconciliation.models import Holding

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Updates the current value of all holdings based on the latest available NAV.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Holding Valuation Update..."))

        try:
            # Optimize: Get distinct schemes that have holdings
            scheme_ids = Holding.objects.values_list('scheme_id', flat=True).distinct()

            updated_count = 0

            for scheme_id in scheme_ids:
                try:
                    # Get latest NAV for this scheme
                    latest_nav = NAVHistory.objects.filter(
                        scheme_id=scheme_id
                    ).order_by('-nav_date').first()

                    if not latest_nav:
                        continue

                    nav_value = latest_nav.net_asset_value

                    # Update all holdings for this scheme
                    # We use bulk update via QuerySet.update() which is efficient
                    # Current Value = Units * Current NAV

                    count = Holding.objects.filter(scheme_id=scheme_id).update(
                        current_nav=nav_value,
                        current_value=F('units') * nav_value,
                        last_updated=timezone.now()
                    )

                    updated_count += count

                except Exception as ex:
                    logger.error(f"Failed to update holdings for scheme {scheme_id}: {ex}")

            self.stdout.write(self.style.SUCCESS(f"Successfully updated valuation for {updated_count} holdings."))

        except Exception as e:
            logger.error(f"Critical error in valuation update: {e}")
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
