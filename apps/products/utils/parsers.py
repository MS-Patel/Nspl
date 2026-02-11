import csv
import logging
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.utils.dateparse import parse_date
from apps.products.models import AMC, Scheme, SchemeCategory, NAVHistory

logger = logging.getLogger(__name__)

def import_schemes_from_file(file_obj):
    """
    Parses a scheme master file (CSV/Pipe) and updates/creates schemes.
    """
    count = 0
    errors = []

    try:
        # Determine format (assume pipe separated like original command)
        decoded_file = file_obj.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file, delimiter='|')

        # Clean headers
        reader.fieldnames = [name.strip() for name in reader.fieldnames]

        for row_idx, row in enumerate(reader, start=1):
            try:
                process_scheme_row(row)
                count += 1
            except Exception as e:
                errors.append(f"Row {row_idx}: {str(e)}")

    except Exception as e:
        errors.append(f"File Error: {str(e)}")

    return count, errors

def process_scheme_row(row):
    # Reuse logic from import_schemes command (adapted)

    # 1. Get or Create AMC
    amc_code = row.get('AMC Code')
    if not amc_code:
        return

    amc_name = amc_code.replace('_MF', '').replace('_', ' ')
    amc, _ = AMC.objects.get_or_create(code=amc_code, defaults={'name': amc_name})

    # 2. Get or Create Category
    cat_code = row.get('Scheme Type')
    category = None
    if cat_code:
        category, _ = SchemeCategory.objects.get_or_create(
            code=cat_code,
            defaults={'name': cat_code}
        )

    # Helpers
    def parse_bool(val):
        if not val: return False
        val = val.strip().upper()
        return val == 'Y' or val == '1'

    def parse_dt(val): # Renamed to avoid shadowing
        if not val: return None
        val = val.strip()
        if not val: return None
        try:
            return datetime.strptime(val, '%b %d %Y').date()
        except ValueError:
            return None

    def parse_tm(val):
        if not val: return None
        val = val.strip()
        if not val: return None
        try:
            return datetime.strptime(val, '%H:%M:%S').time()
        except ValueError:
            return None

    def parse_dec(val):
        if not val: return 0
        val = str(val).strip()
        if not val: return 0
        try:
            return Decimal(val)
        except:
            return 0

    def parse_int(val):
        if not val: return None
        val = str(val).strip()
        if not val: return None
        try:
            return int(val)
        except ValueError:
            return None

    unique_no = parse_int(row.get('Unique No'))
    scheme_code = row.get('Scheme Code')

    if not scheme_code:
        return

    scheme_data = {
        'amc': amc,
        'category': category,
        'name': row.get('Scheme Name'),
        'isin': row.get('ISIN') or '',
        'rta_scheme_code': row.get('RTA Scheme Code'),
        'amc_scheme_code': row.get('AMC Scheme Code'),
        'scheme_type': row.get('Scheme Type'),
        'scheme_plan': row.get('Scheme Plan'),
        'purchase_allowed': parse_bool(row.get('Purchase Allowed')),
        'purchase_transaction_mode': row.get('Purchase Transaction mode'),
        'min_purchase_amount': parse_dec(row.get('Minimum Purchase Amount')),
        'additional_purchase_amount': parse_dec(row.get('Additional Purchase Amount')),
        'max_purchase_amount': parse_dec(row.get('Maximum Purchase Amount')),
        'purchase_amount_multiplier': parse_dec(row.get('Purchase Amount Multiplier')),
        'purchase_cutoff_time': parse_tm(row.get('Purchase Cutoff Time')),
        'redemption_allowed': parse_bool(row.get('Redemption Allowed')),
        'redemption_transaction_mode': row.get('Redemption Transaction Mode'),
        'min_redemption_qty': parse_dec(row.get('Minimum Redemption Qty')),
        'redemption_qty_multiplier': parse_dec(row.get('Redemption Qty Multiplier')),
        'max_redemption_qty': parse_dec(row.get('Maximum Redemption Qty')),
        'min_redemption_amount': parse_dec(row.get('Redemption Amount - Minimum')),
        'max_redemption_amount': parse_dec(row.get('Redemption Amount – Maximum')),
        'redemption_amount_multiple': parse_dec(row.get('Redemption Amount Multiple')),
        'redemption_cutoff_time': parse_tm(row.get('Redemption Cut off Time')),
        'is_sip_allowed': parse_bool(row.get('SIP FLAG')),
        'is_stp_allowed': parse_bool(row.get('STP FLAG')),
        'is_swp_allowed': parse_bool(row.get('SWP Flag')),
        'is_switch_allowed': parse_bool(row.get('Switch FLAG')),
        'start_date': parse_dt(row.get('Start Date')),
        'end_date': parse_dt(row.get('End Date')),
        'reopening_date': parse_dt(row.get('ReOpening Date')),
        'face_value': parse_dec(row.get('Face Value') or '0'),
        'settlement_type': row.get('SETTLEMENT TYPE'),
        'unique_no': unique_no,
        'rta_agent_code': row.get('RTA Agent Code'),
        'amc_active_flag': parse_bool(row.get('AMC Active Flag')),
        'dividend_reinvestment_flag': parse_bool(row.get('Dividend Reinvestment Flag')),
        'amc_ind': row.get('AMC_IND'),
        'exit_load_flag': parse_bool(row.get('Exit Load Flag')),
        'exit_load': row.get('Exit Load'),
        'lock_in_period_flag': parse_bool(row.get('Lock-in Period Flag')),
        'lock_in_period': row.get('Lock-in Period'),
        'channel_partner_code': row.get('Channel Partner Code'),
    }

    scheme = None
    if unique_no:
        scheme = Scheme.objects.filter(unique_no=unique_no).first()
    if not scheme and scheme_code:
        scheme = Scheme.objects.filter(scheme_code=scheme_code).first()

    if scheme:
        for key, value in scheme_data.items():
            setattr(scheme, key, value)
        scheme.save()
    else:
        Scheme.objects.create(scheme_code=scheme_code, **scheme_data)


def import_navs_from_file(file_obj):
    """
    Parses a generic CSV for NAV history.
    Expected Columns: Scheme Code, Date (YYYY-MM-DD or DD-MM-YYYY), NAV
    """
    count = 0
    errors = []

    try:
        decoded_file = file_obj.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)

        # Identify columns flexibly
        cols = reader.fieldnames
        scheme_col = next((c for c in cols if 'scheme' in c.lower() and 'code' in c.lower()), None)
        date_col = next((c for c in cols if 'date' in c.lower()), None)
        nav_col = next((c for c in cols if 'nav' in c.lower() or 'value' in c.lower()), None)

        if not (scheme_col and date_col and nav_col):
            return 0, [f"Missing required columns. Found: {cols}"]

        new_navs = []

        # Batch create buffer
        BATCH_SIZE = 1000

        for row_idx, row in enumerate(reader, start=1):
            try:
                s_code = row[scheme_col].strip()
                date_str = row[date_col].strip()
                nav_val = row[nav_col].strip()

                if not (s_code and date_str and nav_val):
                    continue

                # Find Scheme
                scheme = Scheme.objects.filter(scheme_code=s_code).first()
                if not scheme:
                    # Try RTA Code
                    scheme = Scheme.objects.filter(rta_scheme_code=s_code).first()

                if not scheme:
                    errors.append(f"Row {row_idx}: Scheme not found for code {s_code}")
                    continue

                # Parse Date
                parsed_date = None
                for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
                    try:
                        parsed_date = datetime.strptime(date_str, fmt).date()
                        break
                    except ValueError:
                        continue

                if not parsed_date:
                    errors.append(f"Row {row_idx}: Invalid date format {date_str}")
                    continue

                # Parse NAV
                try:
                    nav_decimal = Decimal(nav_val)
                except:
                    errors.append(f"Row {row_idx}: Invalid NAV {nav_val}")
                    continue

                # Check existence
                if not NAVHistory.objects.filter(scheme=scheme, nav_date=parsed_date).exists():
                    new_navs.append(NAVHistory(
                        scheme=scheme,
                        nav_date=parsed_date,
                        net_asset_value=nav_decimal
                    ))
                    count += 1

                if len(new_navs) >= BATCH_SIZE:
                    NAVHistory.objects.bulk_create(new_navs)
                    new_navs = []

            except Exception as e:
                errors.append(f"Row {row_idx}: {str(e)}")

        if new_navs:
            NAVHistory.objects.bulk_create(new_navs)

    except Exception as e:
        errors.append(f"File Error: {str(e)}")

    return count, errors
