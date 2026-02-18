from django import template

register = template.Library()

@register.filter
def readable_txn_type(value):
    """
    Converts RTA transaction codes to human-readable names.
    If the value is not in the map, returns the original value.
    """
    if not value:
        return ''

    code = str(value).strip().upper()

    mapping = {
        # Purchases
        'P': 'Purchase',
        'PUR': 'Purchase',
        'SIP': 'SIP Purchase',
        'L': 'Lumpsum Purchase',
        'NFO': 'NFO Purchase',
        'ADD': 'Additional Purchase',
        'AP': 'Additional Purchase',

        # Redemptions
        'R': 'Redemption',
        'RED': 'Redemption',
        'SWP': 'SWP Redemption',

        # Switches
        'SI': 'Switch In',
        'SWIN': 'Switch In',
        'STI': 'Switch In',
        'SO': 'Switch Out',
        'SWOUT': 'Switch Out',
        'STO': 'Switch Out',
        'STP': 'STP Transfer',
        'TI': 'Transfer In',
        'TO': 'Transfer Out',

        # Dividends
        'DR': 'Dividend Reinvestment',
        'DIR': 'Dividend Reinvestment',
        'DP': 'Dividend Payout',
        'DIP': 'Dividend Payout',
        'DIV': 'Dividend',

        # Reversals / Corrections
        'PR': 'Purchase Reversal',
        'RR': 'Redemption Reversal',
        'J': 'Journal Entry',
        'RJ': 'Rejection',

        # Others
        'B': 'Bonus',
        'BON': 'Bonus',
        'M': 'Merger',
        'DEMERGER': 'Demerger',
    }

    return mapping.get(code, value)

@register.filter
def txn_badge_class(txn):
    """
    Returns the CSS class for the transaction badge based on type and units.
    """
    if not txn:
        return 'bg-slate-150 text-slate-800'

    code = str(txn.txn_type_code).strip().upper()
    units = float(txn.units) if txn.units else 0

    # Negative units usually mean Outflow, but sometimes RTA reports positive units for Redemptions
    # We prioritize Code

    outflow_codes = ['R', 'RED', 'SWP', 'SO', 'SWOUT', 'STO', 'TO', 'DP', 'DIP', 'PR', 'RJ']
    inflow_codes = ['P', 'PUR', 'SIP', 'L', 'NFO', 'ADD', 'AP', 'SI', 'SWIN', 'STI', 'TI', 'DR', 'DIR', 'B', 'BON', 'RR']

    if code in outflow_codes:
        return 'bg-error/10 text-error'
    elif code in inflow_codes:
        return 'bg-success/10 text-success'

    # Fallback to Unit sign
    if units < 0:
        return 'bg-error/10 text-error'
    elif units > 0:
        return 'bg-success/10 text-success'

    return 'bg-slate-150 text-slate-800'
