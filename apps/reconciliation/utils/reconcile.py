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

        # Ensure fallback actions are correctly mapped for unit tests lacking txn_action
        if not action:
            if t_code == 'P': action = 'ADD'
            elif t_code == 'R': action = 'SUB'
            elif t_code == 'DR': action = 'DIV_REINV'
            elif t_code == 'B': action = 'BONUS'
            elif t_code == 'J': action = None

        # --- APPLY LOGIC ---

        if action == 'ADD':
            if txn.units != 0:
                # WAC Calculation
                # If units are negative but action is ADD, it subtracts units (like a purchase rejection).
                units_added = txn.units
                
                # Only update cost if we are actually adding positive units.
                if units_added > 0:
                    total_cost = (total_units * weighted_avg_cost) + txn.amount
                    total_units += units_added
                    if total_units > 0:
                        weighted_avg_cost = total_cost / total_units
                else:
                    # Negative ADD (Rejection)
                    total_units += units_added
                    # WAC remains the same, just total units drop.

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
            # If units are positive, it's a normal SUB (we deduct).
            # If units are negative, it might be a Redemption Reversal in some RTAs,
            # so subtracting negative units will add them back.
            # But the user specifically said for Karvy: "all rejections have negative units... redemption rejection will have same action SUB thus negating their effect by adding negative units".
            # Wait, if `txn.units` is negative, `total_units -= txn.units` will ADD them back.
            # Wait, the old code had `units_deducted = abs(txn.units)`. If we use `abs()`, a -200 SUB will SUBTRACT 200, which is wrong. We want `txn.units` to dictate the sign, so `-= txn.units` but we must be careful since normally Redemptions are passed as positive units.
            # Usually Redemptions come with POSITIVE units in CAMS. If it's a normal SUB with positive units, `-= txn.units` works correctly.
            # If it's a SUB with NEGATIVE units (Redemption Rejection in Karvy), `-= txn.units` will add them back. This perfectly matches user requirements.

            # Standard Redemption - WAC constant
            total_units -= txn.units
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

def get_cams_transaction_type_and_action(trxn_type):
    """
    Returns a tuple of (trxn_type, action) based on the CAMS transaction type codes starting letter.
    """
    code = str(trxn_type).strip().upper()

    # Priority matching for 2-letter prefixes
    if code.startswith('SI'):
        return code, 'ADD'
    elif code.startswith('SO'):
        return code, 'SUB'
    elif code.startswith('TI'):
        return code, 'ADD'
    elif code.startswith('TO'):
        return code, 'SUB'
    elif code.startswith('DR'):
        return code, 'ADD'

    # Matching for 1-letter prefixes
    if code.startswith('P'):
        return code, 'ADD'
    elif code.startswith('R'):
        return code, 'SUB'
    elif code.startswith('J'):
        return code, None

    return code, None


def get_karvy_transaction_type_and_action(txn_type, desc, t_flag=""):
    """
    Returns a tuple of (human_readable_type, action) based on the Karvy transaction codes mapping.
    Karvy rejections have negative units, which negates their effect naturally if the action is maintained.
    For example, 'Purchase Rejection' will have action 'ADD' (with negative units, subtracting from total).
    """
    t_type = str(txn_type).strip().upper()
    description = str(desc).strip().upper()
    flag = str(t_flag).strip().upper()

    if "NCT" in description:
        if flag in ["P", "TI", "PI"]:
            return description.title() if description else t_type.title(), "ADD"
        elif flag in ["R", "TO", "SO"]:
            return description.title() if description else t_type.title(), "SUB"

    # Provided Map:
    # Key: Transaction Type Code (txn_type/description mapped) -> Action mapping
    # Action determination:
    # Addition-like: ADD
    # Subtraction-like: SUB

    KARVY_MAPPING = {
        'SIN': ('Systematic Investment', 'ADD'),
        'FUL': ('Redemption', 'SUB'),
        'SIND': ('Systematic Investment Pre-Rejection', 'ADD'),
        'SINR': ('SIP Rejection', 'ADD'),
        'NEW': ('Purchase', 'ADD'),
        'LTOF': ('Lateral Shift Out', 'SUB'),
        'DIV': ('Gross Dividend', 'ADD'), # Gross Dividend usually ADD (reinvested or payout depends, but ADD fits inflow logic if reinvested, usually DIV is DIV_REINV, fallback to ADD for now)
        'RED': ('Redemption', 'SUB'),
        'LTIN': ('Lateral Shift In', 'ADD'),
        'TMI': ('Transmission In', 'ADD'),
        'TRMO': ('Transmission Out', 'SUB'),
        'LTIA': ('Lateral Shift In', 'ADD'),
        'ADD': ('Purchase', 'ADD'),
        'ADDR': ('Purchase Rejection', 'ADD'),
        'NEWR': ('Purchase Rejection', 'ADD'),
        'TMO': ('Transmission Out', 'SUB'),
        'LTOFR': ('Lat. Shift Out Rej.', 'SUB'),
        'LTINR': ('Lat. Shift In Rej.', 'ADD'),
        'TRMI': ('Transmission In', 'ADD'),
        'FULR': ('Redemption Rejection', 'SUB'),
        'IPOD': ('Initial Purchase Pre-Rejection', 'ADD'),
        'IPO': ('Initial Allotment', 'ADD'),
        'NEWD': ('New Purchase Pre-Rejection', 'ADD'),
        'LTOP': ('Lateral Shift Out', 'SUB'),
        'RFD': ('Refund', 'SUB'),
        'IPOR': ('IPO Rejection', 'ADD'),
        'LTIAR': ('Lat. Shift In Rej.', 'ADD'),
        'PLDO': ('Pledging', 'PLEDGE_ADD'), # Usually pledge adds to pledged_units
        'SWOF': ('Switch Over Out', 'SUB'),
        'SWOP': ('Switch Over Out', 'SUB'),
        'FULRR': ('Redemption Rejection Reversal', 'SUB'), # Red Rejection Reversal -> Redeeming again -> SUB
        'TRMOR': ('Transmission Out Rejection', 'SUB'),
        'REDR': ('Redemption Rejection', 'SUB'),
        'REDRR': ('Redemption Rejection Reversal', 'SUB'),
        'SWD': ('Systematic Withdrawal', 'SUB'),
        'ADDD': ('Additional Purchase Pre-Rejection', 'ADD'),
    }

    if t_type in KARVY_MAPPING:
        return KARVY_MAPPING[t_type]
    elif description in KARVY_MAPPING:
        return KARVY_MAPPING[description]

    # Fallback based on text if no exact match is found
    if 'PURCHASE' in description or 'PURCHASE' in t_type or 'INVESTMENT' in description:
        return description.title() if description else t_type.title(), 'ADD'
    elif 'REDEMPTION' in description or 'REDEMPTION' in t_type or 'WITHDRAWAL' in description:
        return description.title() if description else t_type.title(), 'SUB'
    elif 'SWITCH OUT' in description or 'SHIFT OUT' in description:
        return description.title() if description else t_type.title(), 'SUB'
    elif 'SWITCH IN' in description or 'SHIFT IN' in description:
        return description.title() if description else t_type.title(), 'ADD'

    return description.title() if description else t_type.title(), None


def _get_legacy_action(t_code, t_flag, desc, txn):
    """
    Helper for Karvy/Legacy logic
    """
    if txn.source_file and txn.source_file.rta_type == 'KARVY':
        _, action = get_karvy_transaction_type_and_action(t_code, desc, t_flag)
    elif txn.source_file and txn.source_file.rta_type == 'CAMS':
        _, action = get_cams_transaction_type_and_action(txn.txn_type_code)
    else:
        # Fallback for manual or Franklin
        _, action = get_karvy_transaction_type_and_action(t_code, desc, t_flag)

    return action
