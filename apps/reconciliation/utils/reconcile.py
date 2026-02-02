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

    for txn in transactions:
        # Determine direction
        # CAMS/Karvy types: P, R, SI, SO, SIP, etc.
        # We need to standardize checks.

        t_code = txn.txn_type_code.upper()

        # Positive Flows
        if t_code in ['P', 'SI', 'SIP', 'PURCHASE', 'SWITCH IN', 'BSE_SIP', 'TI']:
            # Purchase or Inflow
            # Update WAC
            # New WAC = (Old Value + New Investment) / (Old Units + New Units)

            # Use txn.amount (Total Investment) and txn.units
            # Note: txn.amount is absolute.

            # Handle edge case: Reversal of purchase? Usually RTA sends negative units?
            # CAMS sends negative units for reversals? Or specific code.
            # Assuming standard flows for now.

            if txn.units > 0:
                total_cost = (total_units * weighted_avg_cost) + txn.amount
                total_units += txn.units
                if total_units > 0:
                    weighted_avg_cost = total_cost / total_units

        # Negative Flows
        elif t_code in ['R', 'SO', 'REDEMPTION', 'SWITCH OUT', 'TO']:
            # Redemption or Outflow
            # WAC stays the same, units decrease.
            # RTA parsers usually store units as negative for Redemptions?
            # Let's check parsers.py.
            # Yes: CAMSParser says: effective_units = -abs(units) if R/SO.
            # But the Transaction model stores `units` as the raw value from file?
            # Let's re-read parsers.py carefully.

            # CAMSParser:
            # effective_units = -abs(units) ...
            # Transaction.create(..., units=units, ...) -> It saves the RAW units (usually positive in file).
            # So I need to apply sign here.

            # But wait, CAMSParser update_holding used effective_units.
            # Here in recalculate, I must derive effective units from Type.

            units_to_deduct = abs(txn.units)
            total_units -= units_to_deduct

            # If total units becomes 0 or negative (error case), reset WAC
            if total_units <= 0:
                total_units = Decimal(0)
                weighted_avg_cost = Decimal(0)

        # Pledge Logic (If specific codes exist)
        elif t_code in ['PL', 'PLEDGE']:
            pledged_units += abs(txn.units)
        elif t_code in ['UPL', 'UNPLEDGE']:
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
