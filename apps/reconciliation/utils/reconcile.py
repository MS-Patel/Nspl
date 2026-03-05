from decimal import Decimal
from django.db.models import Sum
from apps.reconciliation.models import Transaction, Holding
from apps.products.models import NAVHistory
from django.utils import timezone
from thefuzz import fuzz

def recalculate_holding(investor, scheme, folio_number):
    """
    Recalculates the Holding snapshot (Units, Avg Cost) based on the Transaction history.
    This ensures that the Holding model is always in sync with the source of truth (Transactions).
    """
    if not investor or not scheme or not folio_number:
        return

    transactions = Transaction.objects.filter(
        investor=investor,
        scheme=scheme,
        folio_number=folio_number
    ).order_by('date', 'created_at')

    total_units = Decimal(0)
    weighted_avg_cost = Decimal(0)

    pledged_units = Decimal(0)
    locked_units = Decimal(0)

    for txn in transactions:
        t_code = txn.txn_type_code.upper().strip()
        t_flag = (txn.tr_flag or "").upper().strip()
        desc = (txn.description or "").upper().strip()
        rta_code = (txn.rta_code or "").upper().strip()

        # Use computed action from DB if available, otherwise calculate fallback
        if txn.txn_action:
            action = txn.txn_action
        else:
            action = _get_legacy_action(t_code, t_flag, desc, txn)

        # --- APPLY LOGIC ---

        if action == 'ADD':
            if txn.units != 0:
                # WAC Calculation
                units_added = abs(txn.units)
                # If units are negative but action is ADD (rare error case), take absolute?
                # Usually ADD implies positive inflow.
                
                total_cost = (total_units * weighted_avg_cost) + abs(txn.amount)
                total_units += units_added
                if total_units > 0:
                    weighted_avg_cost = total_cost / total_units

        elif action == 'DIV_REINV':
            if txn.units > 0:
                total_cost = (total_units * weighted_avg_cost) + txn.amount
                total_units += txn.units
                if total_units > 0:
                    weighted_avg_cost = total_cost / total_units

        elif action == 'BONUS':
             if txn.units > 0:
                # Cost doesn't increase, units do -> WAC decreases
                total_units += txn.units
                if total_units > 0:
                    # New WAC = Old Total Cost / New Total Units
                    current_total_cost = (total_units - txn.units) * weighted_avg_cost
                    weighted_avg_cost = current_total_cost / total_units

        elif action == 'SUB':
            # Redemption or Switch Out
            units_deducted = abs(txn.units)
            # amount_reversed = abs(txn.amount) # Not used for WAC, WAC stays constant on sale

            # Standard Redemption - WAC constant
            total_units -= units_deducted
            if total_units <= 0:
                total_units = Decimal(0)
                weighted_avg_cost = Decimal(0)

        elif action == 'PLEDGE_ADD':
            pledged_units += abs(txn.units)
        elif action == 'PLEDGE_SUB':
            pledged_units -= abs(txn.units)
            if pledged_units < 0: pledged_units = Decimal(0)

    # Final Safety
    if total_units < 0:
        total_units = Decimal(0)

    free_units = total_units - locked_units - pledged_units
    if free_units < 0:
        free_units = Decimal(0)

    # Update Holding
    holding, created = Holding.objects.get_or_create(
        investor=investor,
        scheme=scheme,
        folio_number=folio_number
    )

    holding.units = total_units
    holding.average_cost = weighted_avg_cost
    holding.pledged_units = pledged_units
    holding.locked_units = locked_units
    holding.free_units = free_units

    # Recalculate Current Value if NAV is present
    # Fetch latest NAV
    latest_nav_obj = NAVHistory.objects.filter(scheme=scheme).order_by('-nav_date').first()
    if latest_nav_obj:
        holding.current_nav = latest_nav_obj.net_asset_value

    if holding.current_nav:
        holding.current_value = total_units * holding.current_nav
    else:
        holding.current_value = Decimal(0)

    holding.last_updated = timezone.now()
    holding.save()

def get_transaction_type_and_action(t_code, t_flag, desc, txn_units=0, reversal_code=None):
    """
    Returns a tuple of (human_readable_type, action) based on the transaction codes.
    """
    # PURCHASE / INFLOWS
    PURCHASE_CODES = {
        'P', 'PURCHASE', 'FRESH PURCHASE', 'ADDITIONAL PURCHASE',
        'ADD', 'NEW', 'IPO', 'LTIA', 'LTIN', 'TRFI', 'TRMI', 'CNI', 'DSPA', 'DSPI', 'DSPN'
    }
    SIP_CODES = {
        'SIN', 'STPA', 'STPI', 'STPN', 'STRA', 'STRI', 'SWIA', 'SWIN'
    }

    # REDEMPTION / OUTFLOWS
    REDEMPTION_CODES = {
        'R', 'REDEMPTION', 'SWITCH OUT', 'TRANSFER OUT',
        'FUL', 'RED', 'LTOF', 'LTOP', 'TRFO', 'TRMO', 'CNO', 'DSPO'
    }
    SWP_CODES = {
        'SWD', 'STPO', 'STRO', 'SWOF', 'SWOP'
    }

    # DIVIDEND REINVESTMENT
    DIVIDEND_REINVEST_CODES = {'DR', 'DIR', 'DIVIDEND REINVESTMENT', 'DIVIDEND REINVEST'}

    # BONUS
    BONUS_CODES = {'B', 'BON', 'BONUS', 'BNS'}

    # PLEDGE
    PLEDGE_CODES = {'PL', 'PLEDGE', 'PLDO'}
    UNPLEDGE_CODES = {'UPL', 'UNPLEDGE', 'UPLO'}

    # REVERSALS
    PURCHASE_REVERSAL_CODES = {
        'ADDR', 'ADDRR', 'NEWR', 'NEWRR', 'IPOR', 'IPORR',
        'LTIAR', 'LTIARR', 'LTINR', 'LTINRR', 'TRFIR', 'DSPIR', 'CNIR'
    }
    SIP_REVERSAL_CODES = {
        'SINR', 'SINRR', 'STPAR', 'STPARR', 'STPIR', 'STRAR', 'STRIR', 'SWIAR', 'SWINR'
    }

    REDEMPTION_REVERSAL_CODES = {
        'REDR', 'REDRR', 'FULR', 'FULRR', 'LTOFR', 'LTOFRR',
        'LTOPR', 'LTOPRR', 'TRFOR', 'DSPOR', 'CNOR'
    }
    SWP_REVERSAL_CODES = {
        'SWDR', 'SWDRR', 'STPOR', 'STPORR', 'STROR', 'SWOFR', 'SWOPR'
    }

    GENERIC_REVERSAL_CODES = {'J', 'REV', 'REVERSAL'}

    action = None
    txn_type = None

    if t_code in PURCHASE_CODES:
        action = 'ADD'
        txn_type = 'Purchase'
    elif t_code in SIP_CODES:
        action = 'ADD'
        txn_type = 'SIP'
    elif t_code in REDEMPTION_CODES:
        action = 'SUB'
        txn_type = 'Redemption'
    elif t_code in SWP_CODES:
        action = 'SUB'
        txn_type = 'SWP'
    elif t_code in DIVIDEND_REINVEST_CODES:
        action = 'DIV_REINV'
        txn_type = 'Dividend Reinvestment'
    elif t_code in BONUS_CODES:
        action = 'BONUS'
        txn_type = 'Bonus'
    elif t_code in PURCHASE_REVERSAL_CODES:
        action = 'SUB'
        txn_type = 'Purchase Reversal'
    elif t_code in SIP_REVERSAL_CODES:
        action = 'SUB'
        txn_type = 'SIP Reversal'
    elif t_code in REDEMPTION_REVERSAL_CODES:
        action = 'ADD'
        txn_type = 'Redemption Reversal'
    elif t_code in SWP_REVERSAL_CODES:
        action = 'ADD'
        txn_type = 'SWP Reversal'
    elif t_code in PLEDGE_CODES:
        action = 'PLEDGE_ADD'
        txn_type = 'Pledge'
    elif t_code in UNPLEDGE_CODES:
        action = 'PLEDGE_SUB'
        txn_type = 'Unpledge'
    elif t_code in GENERIC_REVERSAL_CODES:
        if txn_units < 0:
            action = 'SUB'
            txn_type = 'Reversal'
        elif txn_units > 0:
            if "REDEMPTION" in desc or "WITHDRAWAL" in desc:
                action = 'ADD'
                txn_type = 'Redemption Reversal'
            else:
                action = 'SUB'
                txn_type = 'Purchase Reversal'

    if not action and t_flag:
        if t_flag == 'P':
            action = 'ADD'
            txn_type = 'Purchase'
        elif t_flag == 'R':
            action = 'SUB'
            txn_type = 'Redemption'

    if not action and desc:
        if "REVERSAL" in desc or "REJECTION" in desc:
            if "REDEMPTION" in desc or "WITHDRAWAL" in desc:
                action = 'ADD'
                txn_type = 'Redemption Reversal'
            else:
                action = 'SUB'
                txn_type = 'Purchase Reversal'
        elif any(x in desc for x in ["SIP", "SYSTEMATIC INVESTMENT", "STP IN"]):
            action = 'ADD'
            txn_type = 'SIP'
        elif any(x in desc for x in ["PURCHASE", "SWITCH IN", "TRANSFER IN", "NFO"]):
            action = 'ADD'
            txn_type = 'Purchase'
        elif any(x in desc for x in ["SWP", "SYSTEMATIC WITHDRAWAL", "STP OUT"]):
            action = 'SUB'
            txn_type = 'SWP'
        elif any(x in desc for x in ["REDEMPTION", "SWITCH OUT", "TRANSFER OUT"]):
            action = 'SUB'
            txn_type = 'Redemption'
        elif "DIVIDEND REINVEST" in desc:
            action = 'DIV_REINV'
            txn_type = 'Dividend Reinvestment'
        elif "BONUS" in desc:
            action = 'BONUS'
            txn_type = 'Bonus'
        
        if not action:
             if fuzz.partial_ratio("PURCHASE", desc) > 80:
                 action = 'ADD'
                 txn_type = 'Purchase'
             elif fuzz.partial_ratio("REDEMPTION", desc) > 80:
                 action = 'SUB'
                 txn_type = 'Redemption'

    if reversal_code:
        rev_code = str(reversal_code).strip().upper()
        # Only swap if it wasn't already caught by the REVERSAL_CODES dictionaries
        if rev_code in ['R', 'Y', 'REV', 'REVERSAL'] and t_code not in PURCHASE_REVERSAL_CODES and t_code not in REDEMPTION_REVERSAL_CODES and t_code not in GENERIC_REVERSAL_CODES and t_code not in SIP_REVERSAL_CODES and t_code not in SWP_REVERSAL_CODES:
            if action == 'ADD':
                action = 'SUB'
                if txn_type == 'Purchase': txn_type = 'Purchase Reversal'
                elif txn_type == 'SIP': txn_type = 'SIP Reversal'
            elif action == 'SUB':
                action = 'ADD'
                if txn_type == 'Redemption': txn_type = 'Redemption Reversal'
                elif txn_type == 'SWP': txn_type = 'SWP Reversal'

    if not txn_type:
        txn_type = 'Other'

    return txn_type, action

def _get_legacy_action(t_code, t_flag, desc, txn):
    """
    Helper for Karvy/Legacy logic
    """
    _, action = get_transaction_type_and_action(t_code, t_flag, desc, txn.units, getattr(txn, 'reversal_code', None))
    return action
