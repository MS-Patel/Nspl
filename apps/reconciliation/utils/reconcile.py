from decimal import Decimal
from django.db.models import Sum
from apps.reconciliation.models import Transaction, Holding
from django.utils import timezone

def recalculate_holding(investor, scheme, folio_number):
    """
    Recalculates the Holding snapshot (Units, Avg Cost) based on the Transaction history.
    This ensures that the Holding model is always in sync with the source of truth (Transactions).

    Args:
        investor (InvestorProfile): The investor.
        scheme (Scheme): The scheme.
        folio_number (str): The folio number.
    """
    if not investor or not scheme or not folio_number:
        return

    transactions = Transaction.objects.filter(
        investor=investor,
        scheme=scheme,
        folio_number=folio_number
    ).order_by('date', 'created_at')

    total_units = Decimal(0)
    current_value_at_cost = Decimal(0) # Used for WAC calculation
    weighted_avg_cost = Decimal(0)

    pledged_units = Decimal(0)
    # Locked units logic would require scheme type and date checks (ELSS 3 years)
    # For now, we default to 0 or derive from specific transaction types if they existed.
    locked_units = Decimal(0)

    # Standard Transaction Codes (Expanded List)
    PURCHASE_CODES = {'P', 'SI', 'SIP', 'SIN', 'TI', 'PURCHASE', 'SWITCH IN', 'BSE_SIP', 'TRANSFER IN', 'ADDITIONAL PURCHASE', 'FRESH PURCHASE'}
    DIVIDEND_REINVEST_CODES = {'DR', 'DIR', 'DIVIDEND REINVESTMENT'}
    BONUS_CODES = {'B', 'BON', 'BONUS'}
    REDEMPTION_CODES = {'R', 'SO', 'TO', 'REDEMPTION', 'SWITCH OUT', 'TRANSFER OUT'}
    REVERSAL_CODES = {'J', 'REV', 'REVERSAL'}
    PLEDGE_CODES = {'PL', 'PLEDGE'}
    UNPLEDGE_CODES = {'UPL', 'UNPLEDGE'}

    for txn in transactions:
        t_code = txn.txn_type_code.upper().strip()

        # Positive Flows (Purchase/Switch In/SIP)
        if t_code in PURCHASE_CODES:
            # Purchase or Inflow
            # Update WAC
            # New WAC = (Old Value + New Investment) / (Old Units + New Units)

            if txn.units > 0:
                total_cost = (total_units * weighted_avg_cost) + txn.amount
                total_units += txn.units
                if total_units > 0:
                    weighted_avg_cost = total_cost / total_units

        # Dividend Reinvestment (Units Increase, Amount is considered reinvested)
        elif t_code in DIVIDEND_REINVEST_CODES:
             if txn.units > 0:
                # Treated as new purchase at NAV
                total_cost = (total_units * weighted_avg_cost) + txn.amount
                total_units += txn.units
                if total_units > 0:
                    weighted_avg_cost = total_cost / total_units

        # Bonus (Units Increase, Cost Basis of NEW units is 0)
        # So Total Cost stays same, Total Units Increases -> WAC decreases
        elif t_code in BONUS_CODES:
             if txn.units > 0:
                # Total Cost remains same (free units)
                total_cost = (total_units * weighted_avg_cost) # + 0
                total_units += txn.units
                if total_units > 0:
                    weighted_avg_cost = total_cost / total_units

        # Negative Flows (Redemption/Switch Out)
        elif t_code in REDEMPTION_CODES:
            # Redemption or Outflow
            # WAC stays the same, units decrease.

            units_to_deduct = abs(txn.units)
            total_units -= units_to_deduct

            # If total units becomes 0 or negative (error case), reset WAC
            if total_units <= 0:
                total_units = Decimal(0)
                weighted_avg_cost = Decimal(0)

        # Reversals
        # Assuming Reversal of Purchase (J)
        elif t_code in REVERSAL_CODES:
             # If we treat it as a "Negative Purchase":
             units_to_reverse = abs(txn.units)
             amount_to_reverse = abs(txn.amount)

             # Reduce Total Cost and Total Units
             current_total_cost = total_units * weighted_avg_cost
             new_total_cost = current_total_cost - amount_to_reverse
             total_units -= units_to_reverse

             if total_units > 0 and new_total_cost > 0:
                 weighted_avg_cost = new_total_cost / total_units
             elif total_units <= 0:
                 total_units = Decimal(0)
                 weighted_avg_cost = Decimal(0)


        # Pledge Logic (If specific codes exist)
        elif t_code in PLEDGE_CODES:
            pledged_units += abs(txn.units)
        elif t_code in UNPLEDGE_CODES:
            pledged_units -= abs(txn.units)
            if pledged_units < 0: pledged_units = Decimal(0)

    # Final Safety
    if total_units < 0:
        total_units = Decimal(0)

    free_units = total_units - locked_units - pledged_units
    if free_units < 0:
        # Should not happen unless data issue
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
    if holding.current_nav:
        holding.current_value = total_units * holding.current_nav

    holding.last_updated = timezone.now()
    holding.save()
