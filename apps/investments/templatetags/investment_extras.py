from django import template

register = template.Library()

# --- Strict Code Definitions (Synced with apps.reconciliation.utils.reconcile) ---

# PURCHASE / INFLOWS
PURCHASE_CODES = {
    # Standard
    'P', 'PURCHASE', 'FRESH PURCHASE', 'ADDITIONAL PURCHASE',
    'SIP', 'L', 'NFO', 'ADD', 'AP', # Common Short codes

    # Karvy (Inflow)
    'NEW', 'SIN', 'IPO', 'LTIA', 'LTIN', 'STPA', 'STPI', 'STPN',
    'STRA', 'STRI', 'SWIA', 'SWIN', 'TRFI', 'TRMI', 'CNI', 'DSPA', 'DSPI', 'DSPN',
    # CAMS (Inflow)
    'P105US', 'P43E', 'P81ES', 'PIMAAF', 'PIMAAFS', 'P235ES', 'P108US', 'P112US',
    'P122ES', 'P234ES', 'P228ES', 'P121ES', 'PPVF5S', 'P234E', 'PIBBYS', 'PIBBY',
    'PBBYS1', 'P110ES', 'P200ES', 'P230ES', 'P124ES', 'SI10C', 'SI113E', 'P10M',
    'P225E', 'P211E', 'P124E', 'P113US', 'P230E', 'SIMAAF', 'SI123E', 'SI10',
    'P235E', 'SI228E', 'PPVF5', 'P228E', 'P13S', 'P2TSL', 'P14S', 'SIOP6',
    'SITE5', 'SI1LI', 'PIBCYF', 'SO10', 'SI2LI', 'PINFQS', 'P44S', 'PC1S',
    'SIC1', 'PC1', 'SINL', 'PSBF1', 'P43AS', 'P55A', 'P55AS', 'P43A', 'SI43AS',
    'P53AS', 'SI55A', 'P48A', 'P48AS', 'P45AS', 'SI50A', 'P50AS', 'SI42A',
    'SI43A', 'P45A', 'P53A', 'SI48A', 'PIF1', 'P42A', 'P50A', 'SI49A', 'P5IGS',
    'SI13C', 'P1MCFS', 'P1MAFS', 'PEMR46L', 'PKRI46L', 'PSRI46L', 'SI13S',
    'SI4L', 'SI11FX', 'SI15EM', 'P12EL', 'SI15K', 'PSIPM35', 'PSIP31', 'PSIPL32',
    'PSIPL30', 'PSIP35', 'PEQL8', 'PSIP5M', 'PEQL5', 'SIEQL5', 'SIIN2', 'SIIC9',
    'PTGL', 'SIEQL10', 'PEQL12', 'P1IOF', 'P35S', 'P22S', 'SI11', 'SI46',
    'SIM12', 'SI59', 'P1ELS', 'P35', 'PSI01S', 'PJUE9L', 'PSIA18S', 'P0119S',
    'SIAPR18', 'PAPR18', 'SIAPL18', 'P0818', 'P0818S', 'P0220S', 'P0220',
    'SIALP18', 'P1018S', 'P0721S', 'PENY24S', 'P0718S', 'PEDM7S', 'PAPR17',
    'P0319S', 'PSVFJ8S', 'PVFJ18', 'SI18APR', 'PMINFO', 'SI0119', 'P0119',
    'SIAPR17', 'PBC21', 'P0718', 'PEDM17', 'P0319', 'PENY24', 'SI0219',
    'SIARL18', 'SIPAR18', 'SIES19', 'P0721', 'P1SELW', 'P2SSCF', 'P21AS'
}

# REDEMPTION / OUTFLOWS
REDEMPTION_CODES = {
    # Standard
    'R', 'REDEMPTION', 'SWITCH OUT', 'TRANSFER OUT',
    'RED', 'SWP', 'SO', 'SWOUT', 'STO', 'TO', # Common Short codes

    # Karvy (Outflow)
    'FUL', 'SWD', 'LTOF', 'LTOP', 'STPO', 'STRO', 'SWOF', 'SWOP',
    'TRFO', 'TRMO', 'CNO', 'DSPO',

    # CAMS (Outflow)
    'R1', 'SO1', 'TOCOB', 'R1LQ', 'RTE', 'R1NR', 'R1BCF', 'SO10', 'SO3',
    'SO1Z', 'RM1', 'R5', 'R8W', 'SONL', 'SOM1', 'SO7W', 'SO2E', 'R2E',
    'SO2FX', 'SO1LIQ', 'SO3E', 'SO3E', 'R4', 'SO4', 'R13', 'R7', 'R1LM',
    'SOM12', 'SO2', 'R3', 'R10', 'SOEQT'
}

# SWITCH SPECIFIC
SWITCH_IN_CODES = {
    'SI', 'SWIN', 'STI', 'TI', 'SIN', 'STPI', 'STPN', 'SWIA', 'TRFI', 'TRMI',
    'SI10C', 'SI113E', 'SIMAAF', 'SI123E', 'SI10', 'SI228E', 'SIOP6', 'SITE5',
    'SI1LI', 'SI2LI', 'SIC1', 'SINL', 'SI43AS', 'SI55A', 'SI50A', 'SI42A',
    'SI43A', 'SI48A', 'SI49A', 'SI13C', 'SI13S', 'SI4L', 'SI11FX', 'SI15EM',
    'SI15K', 'SIEQL5', 'SIIN2', 'SIIC9', 'SIEQL10', 'SI11', 'SI46', 'SIM12',
    'SI59', 'PSI01S', 'SIAPR18', 'SIAPL18', 'SIALP18', 'SI18APR', 'SI0119',
    'SIAPR17', 'SI0219', 'SIARL18', 'SIPAR18', 'SIES19'
}

SWITCH_OUT_CODES = {
    'SO', 'SWOUT', 'STO', 'TO', 'STPO', 'STRO', 'SWOF', 'SWOP', 'TRFO', 'TRMO',
    'SO1', 'SO10', 'SO3', 'SO1Z', 'SONL', 'SOM1', 'SO7W', 'SO2E', 'SO2FX',
    'SO1LIQ', 'SO3E', 'SO4', 'SOM12', 'SO2', 'SOEQT'
}

# SYSTEMATIC (SIP/SWP/STP)
SIP_CODES = {
    'SIP', 'PSIPM35', 'PSIP31', 'PSIPL32', 'PSIPL30', 'PSIP35', 'PSIP5M', 'PSIPL',
    'ISIP', 'XSIP'
}

# DIVIDEND
DIVIDEND_REINVEST_CODES = {
    'DR', 'DIR', 'DIVIDEND REINVESTMENT', 'DIVIDEND REINVEST', 'DIV', 'DP', 'DIP'
}

# BONUS
BONUS_CODES = {
    'B', 'BON', 'BONUS', 'BNS'
}

# PLEDGE
PLEDGE_CODES = {'PL', 'PLEDGE', 'PLDO'}
UNPLEDGE_CODES = {'UPL', 'UNPLEDGE', 'UPLO'}

# REVERSALS
PURCHASE_REVERSAL_CODES = {
    'PR', 'PURCHASE REVERSAL',
    'ADDR', 'ADDRR', 'NEWR', 'NEWRR', 'SINR', 'SINRR', 'IPOR', 'IPORR',
    'LTIAR', 'LTIARR', 'LTINR', 'LTINRR', 'STPAR', 'STPARR', 'STPIR',
    'STRAR', 'STRIR', 'SWIAR', 'SWINR', 'TRFIR', 'DSPIR', 'CNIR'
}

REDEMPTION_REVERSAL_CODES = {
    'RR', 'REDEMPTION REVERSAL',
    'REDR', 'REDRR', 'FULR', 'FULRR', 'SWDR', 'SWDRR', 'LTOFR', 'LTOFRR',
    'LTOPR', 'LTOPRR', 'STPOR', 'STPORR', 'STROR', 'SWOFR', 'SWOPR',
    'TRFOR', 'DSPOR', 'CNOR'
}

GENERIC_REVERSAL_CODES = {'J', 'RJ', 'REV', 'REVERSAL', 'REJECTION'}


@register.filter
def readable_txn_type(value):
    """
    Converts RTA transaction codes to human-readable names.
    If the value is not in the map, returns the original value.
    """
    if not value:
        return ''

    code = str(value).strip().upper()

    # 1. Specific Overrides First
    if code in PURCHASE_REVERSAL_CODES: return 'Purchase Reversal'
    if code in REDEMPTION_REVERSAL_CODES: return 'Redemption Reversal'
    if code in GENERIC_REVERSAL_CODES: return 'Reversal'

    if code in SIP_CODES: return 'SIP Purchase'
    if code in SWITCH_IN_CODES: return 'Switch In'
    if code in SWITCH_OUT_CODES: return 'Switch Out'

    if code in DIVIDEND_REINVEST_CODES:
        if code in ['DP', 'DIP']: return 'Dividend Payout'
        return 'Dividend Reinvestment'

    if code in BONUS_CODES: return 'Bonus'
    if code in PLEDGE_CODES: return 'Pledge'
    if code in UNPLEDGE_CODES: return 'Unpledge'

    # 2. General Categories
    if code in PURCHASE_CODES: return 'Purchase'
    if code in REDEMPTION_CODES: return 'Redemption'

    # 3. Fallback to Capitalized Original
    return value.title()

@register.filter
def txn_badge_class(txn):
    """
    Returns the CSS class for the transaction badge based on type and units.
    """
    if not txn:
        return 'bg-slate-150 text-slate-800'

    action = txn.txn_action
    units = float(txn.units) if txn.units else 0

    # Inflow Colors (Green)
    if action in ['ADD', 'DIV_REINV', 'BONUS']:
        return 'bg-success/10 text-success'

    # Outflow Colors (Red)
    if action in ['SUB']:
        return 'bg-error/10 text-error'

    # Fallback based on Units
    if units < 0:
        return 'bg-error/10 text-error'
    elif units > 0:
        return 'bg-success/10 text-success'

    return 'bg-slate-150 text-slate-800'
