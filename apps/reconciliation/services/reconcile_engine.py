import logging
from decimal import Decimal
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from apps.reconciliation.models import Transaction, OrderReconciliation

logger = logging.getLogger(__name__)

class ReconcileEngine:
    def __init__(self):
        pass

    def match_bse_order(self, bse_order_id, investor, scheme, amount, order_date, folio_number=None, sip_reg_no=None):
        """
        Attempts to match a BSE Order with an existing RTA Transaction.
        Returns the OrderReconciliation record.
        """
        logger.info(f"Attempting to reconcile BSE Order {bse_order_id}")

        # 1. Date Window +/- 3 days
        date_min = order_date - timedelta(days=3)
        date_max = order_date + timedelta(days=3)

        # Only look for UNKNOWN transactions that haven't been matched yet
        # We also filter out provisional since they are not authoritative RTA records
        candidates = Transaction.objects.filter(
            origin=Transaction.ORIGIN_UNKNOWN,
            investor=investor,
            date__range=[date_min, date_max],
            is_provisional=False,
            bse_order_id__isnull=True  # Ensure it hasn't been matched to another order
        ).order_by('date', 'created_at') # FIFO for multiple same-day redemptions

        best_match = None
        highest_score = 0.0

        for candidate in candidates:
            score = 0.0

            # Folio match (+0.4)
            if folio_number and candidate.folio_number == folio_number:
                score += 0.4
            elif not folio_number and not candidate.folio_number:
                # If both have no folio (e.g. new folio creation), give partial credit to allow matching
                score += 0.2

            # Scheme match (+0.2)
            if scheme and candidate.scheme_id == scheme.id:
                score += 0.2

            # Amount match (+0.2)
            if abs(candidate.amount - amount) < Decimal('1.00'):
                score += 0.2

            # Date match (+0.2)
            date_diff = abs((candidate.date - order_date).days)
            if date_diff <= 2:
                score += 0.2

            # Special Case: SIP Transactions
            if sip_reg_no and candidate.siptrxnno == sip_reg_no:
                # Strong differentiator, boost score significantly
                score += 0.5

            # Special Case: Reversals
            if candidate.reversal_code:
                # Reversals should not be matched as standard completed orders
                score -= 1.0

            # Multiple Redemptions:
            # Same-day, same-amount transactions are allowed and won't be deduplicated by the parser anymore.
            # The `bse_order_id__isnull=True` and `order_by('date')` ensure we pick the first available unmatched one.

            if score > highest_score:
                highest_score = score
                best_match = candidate

        # Decision Logic
        status = OrderReconciliation.STATUS_MISMATCH

        if highest_score >= 0.9:
            status = OrderReconciliation.STATUS_MATCHED
        elif highest_score >= 0.7:
            status = OrderReconciliation.STATUS_PARTIAL

        with transaction.atomic():
            # Create Reconciliation Record
            recon = OrderReconciliation.objects.create(
                order_id=bse_order_id,
                transaction=best_match if highest_score >= 0.7 else None,
                investor=investor,
                scheme=scheme,
                folio_number=folio_number,
                confidence_score=highest_score,
                status=status,
                match_details={
                    "score": highest_score,
                    "candidate_id": best_match.id if best_match else None,
                    "order_amount": str(amount),
                    "order_date": order_date.isoformat(),
                }
            )

            # Update Transaction if Match >= 0.9
            if status == OrderReconciliation.STATUS_MATCHED and best_match:
                # Re-fetch with lock to prevent race condition on same candidate
                locked_txn = Transaction.objects.select_for_update().get(id=best_match.id)
                if not locked_txn.bse_order_id:
                    locked_txn.origin = Transaction.ORIGIN_BSE
                    locked_txn.bse_order_id = bse_order_id
                    locked_txn.matched_at = timezone.now()
                    locked_txn.match_confidence = highest_score
                    locked_txn.save(update_fields=['origin', 'bse_order_id', 'matched_at', 'match_confidence'])
                    logger.info(f"Successfully matched Order {bse_order_id} to Transaction {locked_txn.id} with score {highest_score}")
                else:
                    # Someone else matched it while we were scoring
                    recon.status = OrderReconciliation.STATUS_FAILED
                    recon.match_details['error'] = 'Candidate already matched during lock acquisition'
                    recon.save()
                    logger.warning(f"Failed to match Order {bse_order_id} - Candidate {best_match.id} already matched")

            elif status == OrderReconciliation.STATUS_PARTIAL and best_match:
                logger.warning(f"Partial match for Order {bse_order_id} with Transaction {best_match.id} (Score: {highest_score})")

        return recon
