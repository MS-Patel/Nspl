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

        # Use Standard/Legacy Logic for ALL transactions
        # This covers standard codes like P, R, SI, SO, DR, B, etc.
        action = _get_legacy_action(t_code, t_flag, desc, txn)

        # --- APPLY LOGIC ---

        if action == 'ADD':
            if txn.units != 0:
                # WAC Calculation
                units_added = txn.units
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

def _get_legacy_action(t_code, t_flag, desc, txn):
    """
    Helper for Karvy/Legacy logic
    """
    # PURCHASE / INFLOWS
    PURCHASE_CODES = {
        'P', 'PURCHASE', 'FRESH PURCHASE', 'ADDITIONAL PURCHASE',
        'ADD', 'NEW', 'SIN', 'IPO', 'LTIA', 'LTIN', 'STPA', 'STPI', 'STPN',
        'STRA', 'STRI', 'SWIA', 'SWIN', 'TRFI', 'TRMI', 'CNI', 'DSPA', 'DSPI', 'DSPN'
    }

    # REDEMPTION / OUTFLOWS
    REDEMPTION_CODES = {
        'R', 'REDEMPTION', 'SWITCH OUT', 'TRANSFER OUT',
        'FUL', 'RED', 'SWD', 'LTOF', 'LTOP', 'STPO', 'STRO', 'SWOF', 'SWOP',
        'TRFO', 'TRMO', 'CNO', 'DSPO'
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
        'ADDR', 'ADDRR', 'NEWR', 'NEWRR', 'SINR', 'SINRR', 'IPOR', 'IPORR',
        'LTIAR', 'LTIARR', 'LTINR', 'LTINRR', 'STPAR', 'STPARR', 'STPIR',
        'STRAR', 'STRIR', 'SWIAR', 'SWINR', 'TRFIR', 'DSPIR', 'CNIR'
    }
    REDEMPTION_REVERSAL_CODES = {
        'REDR', 'REDRR', 'FULR', 'FULRR', 'SWDR', 'SWDRR', 'LTOFR', 'LTOFRR',
        'LTOPR', 'LTOPRR', 'STPOR', 'STPORR', 'STROR', 'SWOFR', 'SWOPR',
        'TRFOR', 'DSPOR', 'CNOR'
    }
    GENERIC_REVERSAL_CODES = {'J', 'REV', 'REVERSAL'}

    action = None
    if t_code in PURCHASE_CODES:
        action = 'ADD'
    elif t_code in REDEMPTION_CODES:
        action = 'SUB'
    elif t_code in DIVIDEND_REINVEST_CODES:
        action = 'DIV_REINV'
    elif t_code in BONUS_CODES:
        action = 'BONUS'
    elif t_code in PURCHASE_REVERSAL_CODES:
        action = 'SUB' 
    elif t_code in REDEMPTION_REVERSAL_CODES:
        action = 'ADD' 
    elif t_code in PLEDGE_CODES:
        action = 'PLEDGE_ADD'
    elif t_code in UNPLEDGE_CODES:
        action = 'PLEDGE_SUB'
    elif t_code in GENERIC_REVERSAL_CODES:
        if txn.units < 0:
            action = 'SUB'
        elif txn.units > 0:
            if "REDEMPTION" in desc or "WITHDRAWAL" in desc:
                action = 'ADD'
            else:
                action = 'SUB'

    if not action and t_flag:
        if t_flag == 'P': action = 'ADD'
        elif t_flag == 'R': action = 'SUB'

    if not action and desc:
        if "REVERSAL" in desc or "REJECTION" in desc:
            if "REDEMPTION" in desc or "WITHDRAWAL" in desc:
                action = 'ADD'
            else:
                action = 'SUB'
        elif any(x in desc for x in ["PURCHASE", "SIP", "SYSTEMATIC INVESTMENT", "SWITCH IN", "TRANSFER IN", "NFO"]):
            action = 'ADD'
        elif any(x in desc for x in ["REDEMPTION", "SWITCH OUT", "TRANSFER OUT", "SWP", "SYSTEMATIC WITHDRAWAL"]):
            action = 'SUB'
        elif "DIVIDEND REINVEST" in desc:
            action = 'DIV_REINV'
        elif "BONUS" in desc:
            action = 'BONUS'
        
        if not action:
             if fuzz.partial_ratio("PURCHASE", desc) > 80: action = 'ADD'
             elif fuzz.partial_ratio("REDEMPTION", desc) > 80: action = 'SUB'

    return action
