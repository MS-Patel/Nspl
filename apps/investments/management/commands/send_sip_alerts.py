from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime
from apps.investments.models import SIP
from apps.users.utils.sms import send_sms_with_template
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sends SMS alerts for upcoming SIPs (e.g., due in 7 days)'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        target_date = today + datetime.timedelta(days=7)

        # Fast query instead of Python loop
        sips = SIP.objects.filter(
            status='ACTIVE',
            next_installment_date=target_date
        ).exclude(last_alert_sent_date=today).select_related('investor__user', 'scheme')

        alerts_sent = 0

        for sip in sips:
            mobile_no = sip.investor.mobile
            if mobile_no:
                context = {
                    "user_name": sip.investor.user.name,
                    "amount": f"{sip.amount:,.2f}",
                    "scheme_name": sip.scheme.name,
                    "due_date": target_date.strftime("%d %b %Y")
                }

                self.stdout.write(f"Sending SIP alert SMS to {mobile_no} for SIP {sip.id} due on {target_date}")
                try:
                    response = send_sms_with_template(mobile_no, "sip_alert", context)
                    if response and response.get("status") != "error":
                        sip.last_alert_sent_date = today
                        sip.save(update_fields=['last_alert_sent_date'])
                        alerts_sent += 1
                    else:
                        msg = response.get('message') if response else "Unknown Error"
                        self.stderr.write(f"Failed to send SMS to {mobile_no}: {msg}")
                except Exception as e:
                    logger.error(f"Error sending SIP alert to {mobile_no}: {e}")
                    self.stderr.write(f"Error sending SIP alert to {mobile_no}: {e}")
            else:
                self.stderr.write(f"SIP {sip.id} has no valid mobile number for investor {sip.investor.user.username}.")

        self.stdout.write(self.style.SUCCESS(f'Successfully checked upcoming SIPs. Sent {alerts_sent} SMS alerts.'))
