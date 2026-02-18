from decimal import Decimal
from django.db.models import Sum
from apps.reconciliation.models import Transaction, Holding
from django.utils import timezone
from thefuzz import fuzz

def recalculate_holding(investor, scheme, folio_number):
    """
    Recalculates the Holding snapshot (Units, Avg Cost) based on the Transaction history.
    This ensures that the Holding model is always in sync with the source of truth (Transactions).
    Uses strict code matching first, then flag matching, then fuzzy description matching.
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

    # --- Strict Code Definitions ---
    # Based on User provided Karvy and CAMS lists

    # PURCHASE / INFLOWS
    PURCHASE_CODES = {
        # Standard
        'P', 'PURCHASE', 'FRESH PURCHASE', 'ADDITIONAL PURCHASE',

        # Karvy (Inflow)
        'ADD', 'NEW', 'SIN', 'IPO', 'LTIA', 'LTIN', 'STPA', 'STPI', 'STPN',
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

        # Karvy (Outflow)
        'FUL', 'RED', 'SWD', 'LTOF', 'LTOP', 'STPO', 'STRO', 'SWOF', 'SWOP',
        'TRFO', 'TRMO', 'CNO', 'DSPO',

        # CAMS (Outflow)
        'R1', 'SO1', 'TOCOB', 'R1LQ', 'RTE', 'R1NR', 'R1BCF', 'SO10', 'SO3',
        'SO1Z', 'RM1', 'R5', 'R8W', 'SONL', 'SOM1', 'SO7W', 'SO2E', 'R2E',
        'SO2FX', 'SO1LIQ', 'SO3E', 'SO3E', 'R4', 'SO4', 'R13', 'R7', 'R1LM',
        'SOM12', 'SO2', 'R3', 'R10', 'SOEQT'
    }

    # DIVIDEND REINVESTMENT (Units Increase, Amount Reinvested)
    DIVIDEND_REINVEST_CODES = {
        'DR', 'DIR', 'DIVIDEND REINVESTMENT', 'DIVIDEND REINVEST',
    }

    # BONUS (Units Increase, Cost Basis of NEW units is 0)
    BONUS_CODES = {
        'B', 'BON', 'BONUS', 'BNS'
    }

    # PLEDGE
    PLEDGE_CODES = {'PL', 'PLEDGE', 'PLDO'}
    UNPLEDGE_CODES = {'UPL', 'UNPLEDGE', 'UPLO'}

    # REVERSALS
    # Split based on Type:
    # 1. Purchase Rejection/Reversal -> Removes units (SUB)
    PURCHASE_REVERSAL_CODES = {
        'ADDR', 'ADDRR', 'NEWR', 'NEWRR', 'SINR', 'SINRR', 'IPOR', 'IPORR',
        'LTIAR', 'LTIARR', 'LTINR', 'LTINRR', 'STPAR', 'STPARR', 'STPIR',
        'STRAR', 'STRIR', 'SWIAR', 'SWINR', 'TRFIR', 'DSPIR', 'CNIR'
    }

    # 2. Redemption Rejection/Reversal -> Adds units back (ADD)
    # e.g., Redemption Rejection (REDR) means redemption failed, units should be credited back.
    REDEMPTION_REVERSAL_CODES = {
        'REDR', 'REDRR', 'FULR', 'FULRR', 'SWDR', 'SWDRR', 'LTOFR', 'LTOFRR',
        'LTOPR', 'LTOPRR', 'STPOR', 'STPORR', 'STROR', 'SWOFR', 'SWOPR',
        'TRFOR', 'DSPOR', 'CNOR'
    }

    # 3. Generic Reversal (J, REV) -> Needs context or sign
    GENERIC_REVERSAL_CODES = {'J', 'REV', 'REVERSAL'}

    for txn in transactions:
        t_code = txn.txn_type_code.upper().strip()
        t_flag = (txn.tr_flag or "").upper().strip()
        desc = (txn.description or "").upper().strip()

        action = None # 'ADD', 'SUB', 'DIV_REINV', 'BONUS', 'PLEDGE_ADD', 'PLEDGE_SUB'

        # --- 1. CODE MATCH ---
        if t_code in PURCHASE_CODES:
            action = 'ADD'
        elif t_code in REDEMPTION_CODES:
            action = 'SUB'
        elif t_code in DIVIDEND_REINVEST_CODES:
            action = 'DIV_REINV'
        elif t_code in BONUS_CODES:
            action = 'BONUS'
        elif t_code in PURCHASE_REVERSAL_CODES:
            action = 'SUB' # Reverse a purchase -> remove units
        elif t_code in REDEMPTION_REVERSAL_CODES:
            action = 'ADD' # Reverse a redemption -> add units back
        elif t_code in PLEDGE_CODES:
            action = 'PLEDGE_ADD'
        elif t_code in UNPLEDGE_CODES:
            action = 'PLEDGE_SUB'
        elif t_code in GENERIC_REVERSAL_CODES:
            # Check sign of units first
            if txn.units < 0:
                action = 'SUB' # Explicit negative units
            elif txn.units > 0:
                # If positive, likely adding back units (reversing a redemption?)
                # OR it's a purchase reversal where RTA sends positive units intended to be deducted?
                # Default to SUB if unknown context, but check description
                if "REDEMPTION" in desc or "WITHDRAWAL" in desc:
                    action = 'ADD' # Reverse redemption
                else:
                    action = 'SUB' # Reverse purchase (default assumption for J/REV)

        # --- 2. FLAG MATCH (Fallback) ---
        if not action and t_flag:
            if t_flag == 'P':
                action = 'ADD'
            elif t_flag == 'R':
                action = 'SUB'

        # --- 3. FUZZY DESCRIPTION MATCH (Fallback) ---
        if not action and desc:
            # Keyword checks
            if "REVERSAL" in desc or "REJECTION" in desc:
                # Need to know WHAT is being reversed
                if "REDEMPTION" in desc or "WITHDRAWAL" in desc:
                    action = 'ADD' # Redemption Reversal -> Add back
                else:
                    action = 'SUB' # Purchase Reversal -> Deduct
            elif any(x in desc for x in ["PURCHASE", "SIP", "SYSTEMATIC INVESTMENT", "SWITCH IN", "TRANSFER IN", "NFO"]):
                action = 'ADD'
            elif any(x in desc for x in ["REDEMPTION", "SWITCH OUT", "TRANSFER OUT", "SWP", "SYSTEMATIC WITHDRAWAL"]):
                action = 'SUB'
            elif "DIVIDEND REINVEST" in desc:
                action = 'DIV_REINV'
            elif "BONUS" in desc:
                action = 'BONUS'

            # If still unsure, try Fuzzy
            if not action:
                 if fuzz.partial_ratio("PURCHASE", desc) > 80: action = 'ADD'
                 elif fuzz.partial_ratio("REDEMPTION", desc) > 80: action = 'SUB'

        # --- APPLY LOGIC ---

        if action == 'ADD':
            if txn.units != 0:
                # WAC Calculation
                # If units are negative in file but identified as ADD (e.g. reversal of redemption reversal?), flip sign
                # Usually ADD implies positive inflow.
                units_added = txn.units

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
            # Redemption or Purchase Reversal
            units_deducted = abs(txn.units)
            amount_reversed = abs(txn.amount)

            # If it's a Purchase Reversal, we should reverse cost impact too
            if t_code in PURCHASE_REVERSAL_CODES or ("REVERSAL" in desc and "REDEMPTION" not in desc):
                 current_total_cost = total_units * weighted_avg_cost
                 new_total_cost = current_total_cost - amount_reversed
                 total_units -= units_deducted
                 if total_units > 0 and new_total_cost > 0:
                     weighted_avg_cost = new_total_cost / total_units
                 elif total_units <= 0:
                     total_units = Decimal(0)
                     weighted_avg_cost = Decimal(0)
            else:
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
    if holding.current_nav:
        holding.current_value = total_units * holding.current_nav

    holding.last_updated = timezone.now()
    holding.save()
