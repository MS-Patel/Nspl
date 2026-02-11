import logging
import requests
from datetime import datetime, date
from decimal import Decimal
from lxml import html
from apps.products.models import Scheme, NAVHistory

logger = logging.getLogger(__name__)

BSE_NAV_URL = "https://www.bsestarmf.in/RptNavMaster.aspx"

def fetch_bse_navs(target_date=None):
    """
    Fetches daily NAVs from BSE Star MF and updates the database.
    """
    if target_date is None:
        target_date = date.today()

    # Format date for BSE (e.g., 10-Feb-2026)
    date_str = target_date.strftime("%d-%b-%Y")

    logger.info(f"Starting BSE NAV Fetch for {date_str}...")

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })

    try:
        # Step 1: GET request to fetch ViewState
        logger.info("Fetching ViewState...")
        response = session.get(BSE_NAV_URL, timeout=30)
        response.raise_for_status()

        tree = html.fromstring(response.content)
        viewstate = tree.xpath("//input[@name='__VIEWSTATE']/@value")
        viewstategenerator = tree.xpath("//input[@name='__VIEWSTATEGENERATOR']/@value")
        eventvalidation = tree.xpath("//input[@name='__EVENTVALIDATION']/@value")

        if not viewstate or not eventvalidation:
            logger.error("Failed to extract ViewState or EventValidation.")
            return False

        payload = {
            '__VIEWSTATE': viewstate[0],
            '__VIEWSTATEGENERATOR': viewstategenerator[0] if viewstategenerator else '',
            '__EVENTVALIDATION': eventvalidation[0],
            'txtToDate': date_str,
            'btnText': 'Export to Text'
        }

        # Step 2: POST request to download text
        logger.info("Downloading NAV file...")
        post_response = session.post(BSE_NAV_URL, data=payload, timeout=60)
        post_response.raise_for_status()

        content = post_response.text

        # Verify content type or content
        if '<html' in content[:100].lower():
            logger.error("Received HTML instead of text file. Possible error in form submission.")
            return False

    except Exception as e:
        logger.error(f"Network error during BSE NAV fetch: {e}")
        return False

    # Step 3: Parse content
    lines = content.splitlines()
    logger.info(f"Downloaded {len(lines)} lines. Processing...")

    # Cache schemes by ISIN
    schemes_map = {}
    schemes = Scheme.objects.exclude(isin__isnull=True).exclude(isin__exact='')
    for s in schemes:
        schemes_map[s.isin] = s

    updated_count = 0

    for line in lines:
        if not line.strip():
            continue

        parts = line.split('|')
        # Expecting at least 7 columns based on sample
        # 0: Date, 1: Scheme Code, 5: ISIN, 6: NAV
        if len(parts) < 7:
            continue

        try:
            isin = parts[5].strip()
            nav_str = parts[6].strip()

            # Skip if no ISIN or NAV
            if not isin or not nav_str:
                continue

            scheme = schemes_map.get(isin)
            if not scheme:
                # Optionally log missing schemes, but might be noisy
                continue

            nav_value = Decimal(nav_str)

            # The date in the file (parts[0]) is usually YYYY-MM-DD
            file_date_str = parts[0].strip()
            try:
                nav_date = datetime.strptime(file_date_str, '%Y-%m-%d').date()
            except ValueError:
                # Fallback to target_date if parsing fails
                nav_date = target_date

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
            # Continue on individual row errors
            continue

    logger.info(f"BSE NAV Update Complete. Updated {updated_count} records.")
    return True
