from django.core.management.base import BaseCommand
from apps.investments.models import SIPInstallment, SIP, Folio
from apps.reconciliation.models import Transaction
from django.utils import timezone
from django.db.models import Q
import datetime

class Command(BaseCommand):
    help = 'RTA transaction linking and lifecycle intelligence for SIPs'

    def handle(self, *args, **kwargs):
        # 1. Process all RTA transactions that look like SIPs
        # Criteria: has siptrxnno OR txn_nature/type implies SIP
        sip_transactions = Transaction.objects.filter(
            Q(siptrxnno__isnull=False) & ~Q(siptrxnno='') |
            Q(txn_nature__icontains='SIP') |
            Q(txn_type__icontains='SIP') |
            Q(txn_nature__icontains='Systematic') |
            Q(txn_type__icontains='Systematic')
        ).exclude(sip_installments__isnull=False)

        new_sips_created = 0
        installments_matched = 0

        for txn in sip_transactions:
            # Skip missing investor/scheme
            if not txn.investor or not txn.scheme:
                continue

            # Identify if it's a failure based on remarks/reversal_code
            remarks = str(txn.description or '').lower()
            reversal_code = str(txn.reversal_code or '').lower()
            txn_nature = str(txn.txn_nature or '').lower()
            txn_type = str(txn.txn_type or '').lower()

            is_failed = any(kw in remarks for kw in ['fail', 'reject', 'revers']) or \
                        any(kw in reversal_code for kw in ['fail', 'reject', 'revers']) or \
                        any(kw in txn_nature for kw in ['fail', 'reject', 'revers']) or \
                        any(kw in txn_type for kw in ['fail', 'reject', 'revers'])

            # Determine the SIPMaster
            sip = None
            if txn.siptrxnno:
                # Try to find by BSE Reg No (siptrxnno)
                sip = SIP.objects.filter(bse_reg_no=txn.siptrxnno, investor=txn.investor, scheme=txn.scheme).first()

            if not sip:
                # Fallback to matching by investor, scheme, amount, and active status
                # If there are multiple, try to match by folio
                potential_sips = SIP.objects.filter(
                    investor=txn.investor,
                    scheme=txn.scheme,
                    amount=abs(txn.amount)
                )
                if txn.folio_number:
                    # Match specific folio if possible
                    folio_sips = potential_sips.filter(folio__folio_number=txn.folio_number)
                    if folio_sips.exists():
                        potential_sips = folio_sips

                sip = potential_sips.order_by('-created_at').first()

            # If no SIPMaster exists, auto-create one
            if not sip:
                # Try to find or create the Folio
                folio_obj = None
                if txn.folio_number:
                    folio_obj, _ = Folio.objects.get_or_create(
                        investor=txn.investor,
                        folio_number=txn.folio_number
                    )

                sip = SIP.objects.create(
                    investor=txn.investor,
                    scheme=txn.scheme,
                    folio=folio_obj,
                    amount=abs(txn.amount),
                    frequency=SIP.MONTHLY,
                    start_date=txn.date,
                    status=SIP.STATUS_ACTIVE,
                    bse_reg_no=txn.siptrxnno,
                    installment_day=txn.date.day if txn.date else None
                )
                new_sips_created += 1

            # Match or create the SIPInstallment
            # We look for a pending/triggered installment around the txn date.
            installment = SIPInstallment.objects.filter(
                sip_master=sip,
                status__in=[SIPInstallment.STATUS_PENDING, SIPInstallment.STATUS_TRIGGERED, SIPInstallment.STATUS_FAILED],
                expected_amount=abs(txn.amount),
                due_date__range=(txn.date - datetime.timedelta(days=10), txn.date + datetime.timedelta(days=10))
            ).order_by('due_date').first()

            if not installment:
                # Check if it was already matched
                already_matched = SIPInstallment.objects.filter(transaction=txn).exists()
                if already_matched:
                    continue # Already processed

                # Create missing installment
                installment = SIPInstallment.objects.create(
                    sip_master=sip,
                    due_date=txn.date,
                    expected_amount=abs(txn.amount),
                    status=SIPInstallment.STATUS_PENDING
                )

            # Update the installment with RTA intelligence
            installment.transaction = txn
            installment.matched_at = timezone.now()

            # Populate RTA fields
            installment.siptrxnno = txn.siptrxnno
            installment.rta_txn_number = txn.txn_number
            installment.remarks = txn.description
            installment.reversal_code = txn.reversal_code
            installment.status_desc = txn.txn_nature or txn.txn_type

            if is_failed:
                installment.status = SIPInstallment.STATUS_FAILED
                installment.failure_reason = f"RTA reported failure: {remarks} {reversal_code}".strip()
            else:
                installment.status = SIPInstallment.STATUS_SUCCESS
                installment.failure_reason = ""

            installment.save()
            installments_matched += 1

        self.stdout.write(self.style.SUCCESS(f"SIP Reconciliation Complete: {new_sips_created} new SIPs created, {installments_matched} installments matched/updated via RTA data."))
