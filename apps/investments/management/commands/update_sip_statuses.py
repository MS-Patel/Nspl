from django.core.management.base import BaseCommand
from apps.investments.models import SIP, SIPInstallment
from django.utils import timezone
from django.db.models import Q

class Command(BaseCommand):
    help = 'Computes SIP master status dynamically based on installment statuses'

    def handle(self, *args, **kwargs):
        sips = SIP.objects.all()
        active_count = 0
        completed_count = 0
        failed_count = 0

        for sip in sips:
            if sip.status == SIP.STATUS_CANCELLED:
                continue

            installments = sip.sip_installments.all()
            if not installments.exists():
                continue

            # COMPLETED: All installments completed (SUCCESS/FAILED/SKIPPED) and no pending ones in future
            pending_future = installments.filter(status__in=[SIPInstallment.STATUS_PENDING, SIPInstallment.STATUS_TRIGGERED]).exists()

            if not pending_future and (sip.end_date and timezone.now().date() > sip.end_date or sip.installments and installments.count() >= sip.installments):
                 sip.status = SIP.STATUS_COMPLETED
                 sip.save(update_fields=['status'])
                 completed_count += 1
                 continue

            # FAILED: Repeated failures beyond threshold (e.g., 3 consecutive failures)
            # Find the last 3 processed installments sorted by date
            recent_installments = installments.filter(status__in=[SIPInstallment.STATUS_SUCCESS, SIPInstallment.STATUS_FAILED]).order_by('-due_date')[:3]
            if recent_installments.count() >= 3:
                all_failed = all(inst.status == SIPInstallment.STATUS_FAILED for inst in recent_installments)
                if all_failed and sip.status != SIP.STATUS_FAILED:
                    sip.status = SIP.STATUS_FAILED
                    sip.save(update_fields=['status'])
                    failed_count += 1
                    continue

            # ACTIVE: future installments exist and not explicitly cancelled or paused
            if sip.status not in [SIP.STATUS_PAUSED, SIP.STATUS_ACTIVE] and pending_future:
                 sip.status = SIP.STATUS_ACTIVE
                 sip.save(update_fields=['status'])
                 active_count += 1

        self.stdout.write(self.style.SUCCESS(f"Updated SIP Statuses. Active: {active_count}, Completed: {completed_count}, Failed: {failed_count}"))
