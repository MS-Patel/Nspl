from django.core.management.base import BaseCommand
from apps.investments.models import SIP
from apps.investments.services import generate_sip_installments

class Command(BaseCommand):
    help = 'Generates missing installments for all existing ACTIVE/PENDING SIPs.'

    def handle(self, *args, **kwargs):
        sips = SIP.objects.filter(status__in=[SIP.STATUS_ACTIVE, SIP.STATUS_PAUSED, SIP.STATUS_PENDING])
        count = 0
        for sip in sips:
            try:
                generate_sip_installments(sip)
                count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error generating installments for SIP {sip.id}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully processed {count} SIPs for installment generation."))
