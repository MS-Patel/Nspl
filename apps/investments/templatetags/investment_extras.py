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
        'SO': 'Switch Out',
        'SWOUT': 'Switch Out',
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
