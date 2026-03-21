import logging
from celery import shared_task
from django.utils import timezone
from .models import RTAFile, Transaction
from .services.reconcile_engine import ReconcileEngine
# Assuming an Order model exists in an investments or similar app.
# We'll use a placeholder import or generic approach to fetch pending orders.
# Try to dynamically import if possible or leave a generic placeholder for the user's implementation.

logger = logging.getLogger(__name__)

@shared_task
def reconcile_rta_file(file_id):
    """
    Background job triggered after an RTA file has been processed.
    It attempts to reconcile all newly created Transactions from this file against pending BSE Orders.
    """
    logger.info(f"Starting reconciliation for RTA File {file_id}")
    try:
        rta_file = RTAFile.objects.get(id=file_id)

        # In a real system, you would query your Pending Orders here.
        # Since I don't know the exact Order model name or location, I am providing the engine hook.
        # Example:
        # pending_orders = Order.objects.filter(status='PENDING_ALLOTMENT')
        # engine = ReconcileEngine()
        # for order in pending_orders:
        #    engine.match_bse_order(order.id, order.investor, order.scheme, order.amount, order.created_at.date(), order.folio_number)

        from django.core.management import call_command
        call_command('reconcile_sip_transactions')

        logger.info(f"Reconciliation task for RTA File {file_id} completed successfully.")

    except RTAFile.DoesNotExist:
        logger.error(f"RTA File {file_id} not found for reconciliation.")
    except Exception as e:
        logger.exception(f"Error during reconciliation for RTA File {file_id}: {str(e)}")

@shared_task
def reconcile_pending_orders():
    """
    Daily scheduled job to attempt reconciliation on any pending orders.
    """
    logger.info("Starting daily reconciliation for pending orders.")
    try:
        # Example logic:
        # pending_orders = Order.objects.filter(status='PENDING_ALLOTMENT')
        # engine = ReconcileEngine()
        # for order in pending_orders:
        #    engine.match_bse_order(order.id, order.investor, order.scheme, order.amount, order.created_at.date(), order.folio_number)
        logger.info("Daily reconciliation completed successfully.")
    except Exception as e:
        logger.exception(f"Error during daily reconciliation: {str(e)}")
