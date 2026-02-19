import time
import random
import string
import datetime
from decimal import Decimal
from scipy import optimize
from django.utils import timezone
from apps.reconciliation.models import Transaction

def generate_distributor_based_ref(distributor_id):
    """
    Generates a unique reference number embedding the Distributor ID.
    Format: {DistributorID:06d}{TimestampSec:10d}{Random:03d}
    Total Length: 19 characters.
    Example: 0000051705622400123
    """
    if distributor_id is None:
        distributor_id = 0

    # Ensure Distributor ID fits in 6 chars
    dist_str = f"{distributor_id:06d}"

    # Timestamp in seconds (10 digits for current epoch)
    timestamp = int(time.time())

    # 3 random digits
    rand_suffix = ''.join(random.choices(string.digits, k=3))

    return f"{dist_str}{timestamp}{rand_suffix}"

def xnpv(rate, cash_flows):
    """
    Calculate Net Present Value for a schedule of cash flows.
    cash_flows: list of tuples (date, amount)
    rate: annual discount rate
    """
    if rate <= -1.0:
        return float('inf')

    t0 = cash_flows[0][0]
    return sum([cf / ((1.0 + rate) ** ((d - t0).days / 365.0)) for d, cf in cash_flows])

def calculate_xirr(cash_flows, guess=0.1):
    """
    Calculate Internal Rate of Return for irregular cash flows (XIRR).
    cash_flows: list of tuples (date, amount)
    """
    if not cash_flows or len(cash_flows) < 2:
        return None

    # Check if we have at least one positive and one negative cash flow
    has_positive = any(cf > 0 for _, cf in cash_flows)
    has_negative = any(cf < 0 for _, cf in cash_flows)

    if not (has_positive and has_negative):
        return None

    # Sort by date
    cash_flows.sort(key=lambda x: x[0])

    try:
        return optimize.newton(lambda r: xnpv(r, cash_flows), guess)
    except (RuntimeError, OverflowError):
        try:
             # Try a different guess if first fails
            return optimize.newton(lambda r: xnpv(r, cash_flows), -0.1)
        except:
            return None

def get_cash_flows(holding):
    """
    Generates a list of (date, amount) tuples for XIRR calculation.
    """
    transactions = Transaction.objects.filter(
        investor=holding.investor,
        scheme=holding.scheme,
        folio_number=holding.folio_number
    ).order_by('date')

    flows = []

    for txn in transactions:
        amount = float(txn.amount)
        txn_type = txn.txn_type_code.upper()
        tr_flag = (txn.tr_flag or "").upper()

        # Determine Flow Direction
        # Inflows (Investments) -> Negative Cash Flow
        is_purchase = tr_flag == 'P' or txn_type in ['P', 'PURCHASE', 'SIP', 'SWITCH IN', 'ADD', 'NEW', 'SI', 'TI', 'SIN', 'STPI', 'STPA']

        # Outflows (Redemptions) -> Positive Cash Flow
        is_redemption = tr_flag == 'R' or txn_type in ['R', 'REDEMPTION', 'SWITCH OUT', 'SUB', 'SO', 'TO', 'SWOF', 'STPO', 'SWP']

        if is_purchase:
             flows.append((txn.date, -amount))
        elif is_redemption:
             flows.append((txn.date, amount))
        else:
             # Try fuzzy match if needed or ignore (e.g., Reversals, Dividends)
             # Dividend Reinvestment (Units added, Amount reinvested) -> Usually 0 cash flow for XIRR
             pass

    # Add Current Value as final positive cash flow (if non-zero)
    if holding.current_value and holding.current_value > 0:
        flows.append((timezone.now().date(), float(holding.current_value)))

    return flows
