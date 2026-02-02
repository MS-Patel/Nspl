import logging
import datetime
from decimal import Decimal
from django.utils import timezone
from apps.investments.models import Order, Mandate, SIP, Folio
from apps.integration.bse_client import BSEStarMFClient
from apps.reconciliation.models import Transaction, Holding
from apps.reconciliation.utils.reconcile import recalculate_holding

logger = logging.getLogger(__name__)

def sync_pending_orders(user=None, investor=None):
    """
    Syncs the status of pending orders from BSE.
    Updates local Order records with BSE status, remarks, and allotment details.

    Args:
        user: The user requesting the sync (used for role-based filtering).
        investor: Specific investor object to filter orders for (overrides user role logic partially).
    """
    # Instantiate client once to reuse cached Zeep clients internally
    client = BSEStarMFClient()

    # Filter orders that need syncing
    # We focus on SENT_TO_BSE and AWAITING_PAYMENT.
    # APPROVED orders also need check for Allotment.
    # PENDING orders haven't been sent yet, so skip.
    orders_qs = Order.objects.filter(
        status__in=[Order.SENT_TO_BSE, Order.AWAITING_PAYMENT, Order.APPROVED]
    )

    # Apply filtering based on investor if provided (Priority)
    if investor:
        orders_qs = orders_qs.filter(investor=investor)
    elif user:
        # If no specific investor, filter by user role
        if user.user_type == 'ADMIN':
            pass
        elif user.user_type == 'RM':
            orders_qs = orders_qs.filter(distributor__rm__user=user)
        elif user.user_type == 'DISTRIBUTOR':
            orders_qs = orders_qs.filter(distributor__user=user)
        elif user.user_type == 'INVESTOR':
            orders_qs = orders_qs.filter(investor__user=user)

    # Performance Safety: Limit processing if user is Admin and no investor specified
    # to avoid syncing thousands of orders on a page load.
    if user and user.user_type == 'ADMIN' and not investor:
        # Just sync the most recent 20 for dashboard freshness or similar,
        # or remove limit if background task.
        # Since this is synchronous on view load, limiting is wise.
        # However, for 'order_list', the user expects to see updated statuses.
        # We'll rely on the Zeep caching optimization for now.
        pass

    for order in orders_qs:
        if not order.bse_order_id:
            continue

        try:
            # 1. Payment Status Check
            # Only relevant if not yet Approved/Allotted
            if order.status in [Order.SENT_TO_BSE, Order.AWAITING_PAYMENT]:
                payment_resp = client.get_payment_status(
                    client_code=order.investor.ucc_code,
                    order_no=order.bse_order_id
                )

                if payment_resp['status'] == 'success' and 'APPROVED' in payment_resp['remarks'].upper():
                    if order.status != Order.APPROVED:
                        order.status = Order.APPROVED
                        order.bse_remarks = f"{order.bse_remarks} | Payment: {payment_resp['remarks']}"
                        order.save()
                elif payment_resp['status'] == 'success' and 'REJECTED' in payment_resp.get('remarks', '').upper():
                     order.status = Order.REJECTED
                     order.bse_remarks = f"{order.bse_remarks} | Payment: {payment_resp['remarks']}"
                     order.save()

            # 2. Order Status Check (Lifecycle)
            status_resp = client.get_order_status(
                order_no=order.bse_order_id,
                client_code=order.investor.ucc_code
            )

            if status_resp and status_resp.Status == '0' and status_resp.OrderDetails:
                bse_detail = status_resp.OrderDetails[0]
                bse_status_text = bse_detail.OrderStatus.upper() # VALID / INVALID

                if bse_status_text == 'INVALID':
                    order.status = Order.REJECTED
                    order.bse_remarks = bse_detail.OrderRemarks
                    order.save()
                    continue

            # 3. Allotment Check
            # Only if Approved or Sent to BSE (and valid)
            if order.status in [Order.APPROVED, Order.SENT_TO_BSE]:
                allot_resp = client.get_allotment_statement(
                    order_no=order.bse_order_id,
                    client_code=order.investor.ucc_code
                )

                if allot_resp and allot_resp.Status == '0' and allot_resp.AllotmentDetails:
                    details = allot_resp.AllotmentDetails[0]
                    allotted_units = Decimal(details.AllottedUnit) if details.AllottedUnit else Decimal(0)

                    if allotted_units > 0:
                        order.status = Order.ALLOTTED
                        order.allotted_units = allotted_units

                        # Capture Folio if new
                        if details.FolioNo and (not order.folio or order.folio.folio_number != details.FolioNo):
                            folio, created = Folio.objects.get_or_create(
                                investor=order.investor,
                                amc=order.scheme.amc,
                                folio_number=details.FolioNo
                            )
                            order.folio = folio

                        order.bse_remarks = "Allotted Successfully"
                        order.save()

                        # ------------------------------------------------------------------
                        # Create Provisional Transaction and Update Holding
                        # ------------------------------------------------------------------

                        # Determine Scheme and Type
                        if order.transaction_type == Order.SWITCH and order.target_scheme:
                            txn_scheme = order.target_scheme
                            txn_type = 'SI'
                        else:
                            txn_scheme = order.scheme
                            txn_type = 'P' # Default to Purchase for Allotment (incl SIP Child)

                        # Check if transaction exists (Provisional or Confirmed)
                        # We match strictly on BSE Order ID if available
                        existing_txn = Transaction.objects.filter(bse_order_id=order.bse_order_id).exists()

                        if not existing_txn and order.folio:
                            Transaction.objects.create(
                                investor=order.investor,
                                scheme=txn_scheme,
                                folio_number=order.folio.folio_number,
                                rta_code='BSE', # Placeholder
                                txn_type_code=txn_type,
                                txn_number=order.bse_order_id, # Use BSE ID as Temp ID
                                bse_order_id=order.bse_order_id,
                                source=Transaction.SOURCE_BSE,
                                is_provisional=True,
                                date=timezone.now().date(), # Allotment Date approx
                                amount=order.amount,
                                units=allotted_units
                            )

                            # Recalculate Holdings
                            recalculate_holding(
                                investor=order.investor,
                                scheme=txn_scheme,
                                folio_number=order.folio.folio_number
                            )
                        # ------------------------------------------------------------------

        except Exception as e:
            logger.error(f"Error syncing order {order.unique_ref_no}: {e}")
            continue

def sync_pending_mandates(user=None, investor=None):
    """
    Syncs status of pending mandates.
    """
    client = BSEStarMFClient()

    mandates_qs = Mandate.objects.filter(status=Mandate.PENDING).exclude(mandate_id__startswith='TEMP')

    # Filter Logic
    if investor:
        mandates_qs = mandates_qs.filter(investor=investor)
    elif user:
        if user.user_type == 'ADMIN':
            pass
        elif user.user_type == 'RM':
            mandates_qs = mandates_qs.filter(investor__distributor__rm__user=user)
        elif user.user_type == 'DISTRIBUTOR':
            mandates_qs = mandates_qs.filter(investor__distributor__user=user)
        elif user.user_type == 'INVESTOR':
            mandates_qs = mandates_qs.filter(investor__user=user)

    for mandate in mandates_qs:
        try:
            if not mandate.mandate_id:
                continue

            resp = client.get_mandate_status(
                mandate_id=mandate.mandate_id,
                client_code=mandate.investor.ucc_code
            )

            if resp and resp.Status == '0' and resp.MandateDetails:
                detail = resp.MandateDetails[0]
                status_text = detail.Status.upper()

                if "APPROVED" in status_text:
                    mandate.status = Mandate.APPROVED
                    mandate.save()
                elif "REJECTED" in status_text:
                    mandate.status = Mandate.REJECTED
                    mandate.save()

        except Exception as e:
            logger.error(f"Error syncing mandate {mandate.mandate_id}: {e}")
            continue

def sync_sip_child_orders(user=None, investor=None):
    """
    Fetches generated child orders for Active SIPs.
    """
    client = BSEStarMFClient()

    sips_qs = SIP.objects.filter(status=SIP.STATUS_ACTIVE).exclude(bse_reg_no__isnull=True)

    if investor:
        sips_qs = sips_qs.filter(investor=investor)
    elif user:
        if user.user_type == 'INVESTOR':
            sips_qs = sips_qs.filter(investor__user=user)

    for sip in sips_qs:
        try:
            resp = client.get_child_orders(
                regn_no=sip.bse_reg_no,
                client_code=sip.investor.ucc_code,
                plan_type="XSIP"
            )

            if resp and resp.Status == '100' and resp.ChildOrderDetails:
                for child in resp.ChildOrderDetails:
                    bse_order_no = child.OrderNumber

                    if not Order.objects.filter(bse_order_id=bse_order_no).exists():
                        Order.objects.create(
                            investor=sip.investor,
                            distributor=sip.investor.distributor,
                            scheme=sip.scheme,
                            folio=sip.folio,
                            mandate=sip.mandate,
                            sip_reg=sip,
                            transaction_type=Order.PURCHASE,
                            amount=Decimal(child.Amount) if child.Amount else 0,
                            units=Decimal(child.Quantity) if child.Quantity else 0,
                            bse_order_id=bse_order_no,
                            status=Order.SENT_TO_BSE,
                            bse_remarks="SIP Installment fetched from BSE",
                            payment_mode=Order.MANDATE,
                            is_new_folio=False
                        )
                        logger.info(f"Created child order {bse_order_no} for SIP {sip.id}")

        except Exception as e:
            logger.error(f"Error syncing SIP child orders {sip.id}: {e}")
            continue
