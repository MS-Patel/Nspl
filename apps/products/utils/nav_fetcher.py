import requests
import logging
from decimal import Decimal
from datetime import datetime
from apps.products.models import Scheme, NAVHistory

logger = logging.getLogger(__name__)

AMFI_NAV_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"

def fetch_amfi_navs():
    """
    Fetches the daily NAV file from AMFI and updates NAVHistory.
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
    count = 0
    updated_count = 0

    # AMFI Format:
    # Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date

    # Cache schemes by ISIN for faster lookup
    schemes_map = {}
    schemes = Scheme.objects.exclude(isin__isnull=True).exclude(isin__exact='')
    for s in schemes:
        schemes_map[s.isin] = s

    logger.info(f"Loaded {len(schemes_map)} schemes for NAV update.")

    for line in lines:
        if not line or ';' not in line:
            continue

        parts = line.split(';')
        if len(parts) < 6:
            continue

        # Headers or weird lines
        if not parts[0].isdigit():
            continue

        try:
            # We try to match by ISIN (Col 1 or 2)
            isin1 = parts[1].strip()
            isin2 = parts[2].strip()

            scheme = None
            if isin1 in schemes_map:
                scheme = schemes_map[isin1]
            elif isin2 in schemes_map:
                scheme = schemes_map[isin2]

            if not scheme:
                continue

            nav_str = parts[4].strip()
            date_str = parts[5].strip()

            if nav_str == 'N.A.':
                continue

            nav_value = Decimal(nav_str)
            nav_date = datetime.strptime(date_str, '%d-%b-%Y').date()

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
            continue

    logger.info(f"NAV Update Complete. Updated {updated_count} records.")
    return True
