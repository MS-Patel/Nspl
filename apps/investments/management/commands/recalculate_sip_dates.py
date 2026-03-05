from django.core.management.base import BaseCommand
from apps.investments.models import SIP

class Command(BaseCommand):
    help = 'Recalculates the next_installment_date for all active SIPs'

    def handle(self, *args, **kwargs):
        sips = SIP.objects.filter(status='ACTIVE')
        count = 0
        for sip in sips:
            sip.calculate_next_installment_date(save=True)
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully recalculated dates for {count} active SIPs.'))
