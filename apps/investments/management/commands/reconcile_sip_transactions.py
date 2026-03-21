from django.core.management.base import BaseCommand
from apps.investments.models import SIPInstallment, SIP
from apps.reconciliation.models import Transaction
from django.utils import timezone
import datetime

class Command(BaseCommand):
    help = 'RTA transaction linking for SIPs'

    def handle(self, *args, **kwargs):
        # We need to find transactions that could be SIPs
        unmatched_installments = SIPInstallment.objects.filter(
            status__in=[SIPInstallment.STATUS_PENDING, SIPInstallment.STATUS_TRIGGERED, SIPInstallment.STATUS_FAILED]
        )

        matched_count = 0

        for installment in unmatched_installments:
            sip = installment.sip_master
            # Matching window: due_date ± 5 days
            start_date = installment.due_date - datetime.timedelta(days=5)
            end_date = installment.due_date + datetime.timedelta(days=5)

            # Potential matches by siptrxnno / bse_reg_no
            if sip.bse_reg_no:
                txn = Transaction.objects.filter(
                    siptrxnno=sip.bse_reg_no,
                    date__range=(start_date, end_date),
                    amount=installment.expected_amount,
                    scheme=sip.scheme
                ).exclude(sip_installments__isnull=False).first()

                if not txn:
                    # Fallback to general matching
                    txn = Transaction.objects.filter(
                        date__range=(start_date, end_date),
                        amount=installment.expected_amount,
                        scheme=sip.scheme,
                        folio_number=sip.folio.folio_number if sip.folio else None,
                    ).exclude(txn_type_code__in=['RED', 'SWO']).exclude(sip_installments__isnull=False).first() # Exclude known non-purchases

                if txn and txn.amount == installment.expected_amount:
                    installment.transaction = txn
                    installment.status = SIPInstallment.STATUS_SUCCESS
                    installment.matched_at = timezone.now()
                    installment.save(update_fields=['transaction', 'status', 'matched_at'])
                    matched_count += 1
            else:
                 # Match without siptrxnno but with exact amount, date, scheme, and folio
                 txn = Transaction.objects.filter(
                    date__range=(start_date, end_date),
                    amount=installment.expected_amount,
                    scheme=sip.scheme,
                    folio_number=sip.folio.folio_number if sip.folio else None,
                 ).exclude(txn_type_code__in=['RED', 'SWO']).exclude(sip_installments__isnull=False).first()

                 if txn and txn.amount == installment.expected_amount:
                    installment.transaction = txn
                    installment.status = SIPInstallment.STATUS_SUCCESS
                    installment.matched_at = timezone.now()
                    installment.save(update_fields=['transaction', 'status', 'matched_at'])
                    matched_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully reconciled {matched_count} SIP transactions."))
