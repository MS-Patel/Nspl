import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.investments.models import SIPInstallment, SIP

class Command(BaseCommand):
    help = 'Daily job to mark upcoming SIP installments as PENDING/TRIGGERED and check for failures'

    def handle(self, *args, **kwargs):
        today = datetime.date.today()
        # threshold days after due date to mark as FAILED
        failure_threshold_days = 5

        # 1. Check for Skipped (if SIP was Paused during this period)
        # Must be done BEFORE marking PENDING as TRIGGERED
        skipped = 0
        paused_installments = SIPInstallment.objects.filter(
            status=SIPInstallment.STATUS_PENDING,
            due_date__lte=today,
            sip_master__status=SIP.STATUS_PAUSED
        )
        for installment in paused_installments:
            installment.status = SIPInstallment.STATUS_SKIPPED
            installment.failure_reason = "SIP was paused."
            installment.save(update_fields=['status', 'failure_reason', 'updated_at'])
            skipped += 1

        if skipped > 0:
             self.stdout.write(self.style.SUCCESS(f"Marked {skipped} installments as SKIPPED due to Paused status."))

        # 2. Mark past due PENDING installments as TRIGGERED
        triggered = SIPInstallment.objects.filter(
            status=SIPInstallment.STATUS_PENDING,
            due_date__lte=today
        ).update(status=SIPInstallment.STATUS_TRIGGERED, updated_at=timezone.now())

        self.stdout.write(self.style.SUCCESS(f"Marked {triggered} installments as TRIGGERED."))

        # 3. Check for Failures (No RTA match after X days)
        cutoff_date = today - datetime.timedelta(days=failure_threshold_days)
        failed = SIPInstallment.objects.filter(
            status=SIPInstallment.STATUS_TRIGGERED,
            due_date__lte=cutoff_date
        ).update(
            status=SIPInstallment.STATUS_FAILED,
            failure_reason="No RTA transaction received within threshold window.",
            updated_at=timezone.now()
        )

        self.stdout.write(self.style.SUCCESS(f"Marked {failed} installments as FAILED."))
