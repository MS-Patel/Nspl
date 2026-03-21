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
        cancelled_count = 0
        paused_count = 0

        today = timezone.now().date()

        for sip in sips:
            if sip.status == SIP.STATUS_COMPLETED:
                continue

            installments = sip.sip_installments.all().order_by('due_date')
            if not installments.exists():
                continue

            # COMPLETED: All installments completed (SUCCESS/FAILED/SKIPPED) and no pending ones in future
            pending_future = installments.filter(status__in=[SIPInstallment.STATUS_PENDING, SIPInstallment.STATUS_TRIGGERED]).exists()

            if not pending_future and (sip.end_date and today > sip.end_date or sip.installments and installments.count() >= sip.installments):
                 sip.status = SIP.STATUS_COMPLETED
                 sip.save(update_fields=['status'])
                 completed_count += 1
                 continue

            # CANCELLED vs PAUSED detection
            # Find the most recent strictly past/processed installments
            recent_installments = installments.filter(
                status__in=[SIPInstallment.STATUS_SUCCESS, SIPInstallment.STATUS_FAILED, SIPInstallment.STATUS_SKIPPED],
                due_date__lte=today
            ).order_by('-due_date')[:3]

            if recent_installments.count() >= 3:
                all_failed = all(inst.status == SIPInstallment.STATUS_FAILED for inst in recent_installments)
                if all_failed and sip.status != SIP.STATUS_CANCELLED:
                    sip.status = SIP.STATUS_CANCELLED
                    sip.failure_reason = "Cancelled due to 3 consecutive failures."
                    sip.save(update_fields=['status', 'failure_reason'])
                    cancelled_count += 1
                    continue

            # PAUSE Detection
            # If the last 2 installments were marked as FAILED but lack explicit RTA/BSE failure reasons,
            # or simply skipped, we can assume it might be paused.
            # A more robust pause check: if it's missing entirely (failed due to timeout) for 1-2 months.
            if recent_installments.count() >= 2 and sip.status not in [SIP.STATUS_CANCELLED, SIP.STATUS_COMPLETED]:
                last_two = recent_installments[:2]
                both_timed_out = all(
                    inst.status == SIPInstallment.STATUS_FAILED and
                    "No RTA transaction received" in str(inst.failure_reason)
                    for inst in last_two
                )
                if both_timed_out and sip.status != SIP.STATUS_PAUSED:
                    sip.status = SIP.STATUS_PAUSED
                    sip.failure_reason = "Paused due to consecutive missing installments."
                    sip.save(update_fields=['status', 'failure_reason'])
                    paused_count += 1
                    continue

            # ACTIVE: future installments exist and not explicitly cancelled or paused
            if sip.status not in [SIP.STATUS_PAUSED, SIP.STATUS_ACTIVE, SIP.STATUS_CANCELLED] and pending_future:
                 sip.status = SIP.STATUS_ACTIVE
                 sip.save(update_fields=['status'])
                 active_count += 1

        self.stdout.write(self.style.SUCCESS(f"Updated SIP Statuses. Active: {active_count}, Completed: {completed_count}, Cancelled: {cancelled_count}, Paused: {paused_count}"))
