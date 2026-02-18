import requests
import logging
from collections import defaultdict
from decimal import Decimal
from datetime import datetime
from django.db.models import Q
from apps.products.models import Scheme, NAVHistory

logger = logging.getLogger(__name__)

AMFI_NAV_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"

def fetch_amfi_navs():
    """
    Fetches the daily NAV file from AMFI and updates NAVHistory.
    Supports updating multiple schemes if they share the same AMFI Code or ISIN.
    """
    logger.info("Starting NAV Fetch from AMFI...")
    try:
        response = requests.get(AMFI_NAV_URL, timeout=30)
        response.raise_for_status()
        content = response.text
    except Exception as e:
        logger.error(f"Failed to fetch NAV file: {e}")
        return False

    lines = content.splitlines()
    updated_count = 0

    # AMFI Format:
    # Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date

    # Build maps for multi-match
    amfi_map = defaultdict(list)
    isin_map = defaultdict(list)

    # Load schemes that have either AMFI Code or ISIN
    schemes = Scheme.objects.filter(Q(amfi_code__isnull=False) | Q(isin__isnull=False))

    for s in schemes:
        if s.amfi_code:
            amfi_map[str(s.amfi_code).strip()].append(s)
        if s.isin:
            isin_map[str(s.isin).strip()].append(s)

    logger.info(f"Loaded {schemes.count()} schemes for NAV update.")

    for line in lines:
        if not line or ';' not in line:
            continue

        parts = line.split(';')
        if len(parts) < 6:
            continue

        # Headers or weird lines (AMFI Code must be digit)
        if not parts[0].isdigit():
            continue

        try:
            amfi_code = parts[0].strip()
            isin1 = parts[1].strip()
            isin2 = parts[2].strip()

            matched_schemes = set()

            # Match by AMFI Code
            if amfi_code in amfi_map:
                matched_schemes.update(amfi_map[amfi_code])

            # Match by ISINs
            if isin1 and isin1 in isin_map:
                matched_schemes.update(isin_map[isin1])
            if isin2 and isin2 in isin_map:
                matched_schemes.update(isin_map[isin2])

            if not matched_schemes:
                continue

            nav_str = parts[4].strip()
            date_str = parts[5].strip()

            if nav_str == 'N.A.':
                continue

            nav_value = Decimal(nav_str)
            nav_date = datetime.strptime(date_str, '%d-%b-%Y').date()

            for scheme in matched_schemes:
                # Update or Create NAVHistory
                obj, created = NAVHistory.objects.get_or_create(
                    scheme=scheme,
                    nav_date=nav_date,
                    defaults={'net_asset_value': nav_value}
                )

                if not created and obj.net_asset_value != nav_value:
                    obj.net_asset_value = nav_value
                    obj.save()

                updated_count += 1

        except Exception as e:
            # logger.warning(f"Error processing line: {line[:50]}... - {e}")
            continue

    logger.info(f"NAV Update Complete. Updated {updated_count} records.")
    return True
