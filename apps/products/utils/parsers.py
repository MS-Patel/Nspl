import csv
import logging
import pandas as pd
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.utils.dateparse import parse_date
from apps.products.models import AMC, Scheme, SchemeCategory, NAVHistory

logger = logging.getLogger(__name__)

def read_file_to_dicts(file_obj):
    """
    Reads a CSV or Excel file and returns a list of dictionaries.
    Keys are normalized (lowercase, stripped).
    """
    data = []
    filename = file_obj.name.lower()

    try:
        if filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file_obj)
            df = df.fillna('')
            records = df.to_dict('records')
            data = [{str(k).strip().lower(): v for k, v in row.items()} for row in records]
        else:
            # Detect delimiter? Original was pipe |
            decoded_file = file_obj.read().decode('utf-8').splitlines()
            # Try sniffing
            try:
                dialect = csv.Sniffer().sniff(decoded_file[0])
                delimiter = dialect.delimiter
            except:
                delimiter = '|' # Default fallback

            reader = csv.DictReader(decoded_file, delimiter=delimiter)
            reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
            data = list(reader)
    except Exception as e:
        logger.error(f"Error reading file {filename}: {e}")
        raise ValueError(f"Error reading file: {str(e)}")

    return data

def import_schemes_from_file(file_obj):
    """
    Parses a scheme master file (CSV/Pipe/Excel) and updates/creates schemes.
    """
    count = 0
    errors = []

    try:
        rows = read_file_to_dicts(file_obj)

        for row_idx, row in enumerate(rows, start=1):
            try:
                process_scheme_row(row)
                count += 1
            except Exception as e:
                errors.append(f"Row {row_idx}: {str(e)}")

    except Exception as e:
        errors.append(f"File Error: {str(e)}")

    return count, errors

def process_scheme_row(row):
    # Keys are lowercase now

    # 1. Get or Create AMC
    amc_code = str(row.get('amc code', '')).strip()
    if not amc_code:
        return

    amc_name = amc_code.replace('_MF', '').replace('_', ' ')
    amc, _ = AMC.objects.get_or_create(code=amc_code, defaults={'name': amc_name})

    # 2. Get or Create Category
    # Support 'category code' (Export) or fallback to 'scheme type' (Legacy/Import)
    cat_code = str(row.get('category code') or row.get('category') or row.get('scheme type') or '').strip()

    category = None
    if cat_code:
        category, _ = SchemeCategory.objects.get_or_create(
            code=cat_code,
            defaults={'name': row.get('category') or cat_code}
        )

    # Helpers
    def parse_bool(val):
        if not val: return False
        val = str(val).strip().lower()
        return val in ['y', 'yes', '1', 'true']

    def parse_dt(val):
        if not val: return None
        # Handle pandas timestamp
        if isinstance(val, (datetime, pd.Timestamp)):
            return val.date()

        val = str(val).strip()
        if not val: return None

        for fmt in ('%b %d %Y', '%Y-%m-%d', '%d-%m-%Y'):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
        return None

    def parse_tm(val):
        if not val: return None
        val = str(val).strip()
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
            return int(float(val)) # Handle 1.0 from float
        except ValueError:
            return None

    unique_no = parse_int(row.get('unique no'))
    scheme_code = str(row.get('scheme code', '')).strip()

    if not scheme_code:
        return

    scheme_data = {
        'amc': amc,
        'category': category,
        'name': row.get('scheme name') or row.get('name'),
        'isin': row.get('isin') or '',
        'rta_scheme_code': row.get('rta scheme code'),
        'amc_scheme_code': row.get('amc scheme code'),
        'scheme_type': row.get('scheme type'),
        'scheme_plan': row.get('scheme plan'),
        'purchase_allowed': parse_bool(row.get('purchase allowed') or row.get('purchase allowed (y/n)')),
        'purchase_transaction_mode': row.get('purchase transaction mode'),
        'min_purchase_amount': parse_dec(row.get('minimum purchase amount') or row.get('min purchase amount')),
        'additional_purchase_amount': parse_dec(row.get('additional purchase amount')),
        'max_purchase_amount': parse_dec(row.get('maximum purchase amount') or row.get('max purchase amount')),
        'purchase_amount_multiplier': parse_dec(row.get('purchase amount multiplier')),
        'purchase_cutoff_time': parse_tm(row.get('purchase cutoff time')),
        'redemption_allowed': parse_bool(row.get('redemption allowed') or row.get('redemption allowed (y/n)')),
        'redemption_transaction_mode': row.get('redemption transaction mode'),
        'min_redemption_qty': parse_dec(row.get('minimum redemption qty') or row.get('min redemption qty')),
        'redemption_qty_multiplier': parse_dec(row.get('redemption qty multiplier')),
        'max_redemption_qty': parse_dec(row.get('maximum redemption qty') or row.get('max redemption qty')),
        'min_redemption_amount': parse_dec(row.get('redemption amount - minimum') or row.get('min redemption amount')),
        'max_redemption_amount': parse_dec(row.get('redemption amount – maximum') or row.get('max redemption amount')),
        'redemption_amount_multiple': parse_dec(row.get('redemption amount multiple')),
        'redemption_cutoff_time': parse_tm(row.get('redemption cut off time') or row.get('redemption cutoff time')),
        'is_sip_allowed': parse_bool(row.get('sip flag') or row.get('sip allowed (y/n)')),
        'is_stp_allowed': parse_bool(row.get('stp flag') or row.get('stp allowed (y/n)')),
        'is_swp_allowed': parse_bool(row.get('swp flag') or row.get('swp allowed (y/n)')),
        'is_switch_allowed': parse_bool(row.get('switch flag') or row.get('switch allowed (y/n)')),
        'start_date': parse_dt(row.get('start date')),
        'end_date': parse_dt(row.get('end date')),
        'reopening_date': parse_dt(row.get('reopening date')),
        'face_value': parse_dec(row.get('face value') or '0'),
        'settlement_type': row.get('settlement type'),
        'unique_no': unique_no,
        'rta_agent_code': row.get('rta agent code'),
        'amc_active_flag': parse_bool(row.get('amc active flag') or row.get('amc active flag (y/n)')),
        'dividend_reinvestment_flag': parse_bool(row.get('dividend reinvestment flag') or row.get('dividend reinvestment flag (y/n)')),
        'amc_ind': row.get('amc_ind'),
        'exit_load_flag': parse_bool(row.get('exit load flag') or row.get('exit load flag (y/n)')),
        'exit_load': row.get('exit load'),
        'lock_in_period_flag': parse_bool(row.get('lock-in period flag') or row.get('lock-in period flag (y/n)')),
        'lock_in_period': row.get('lock-in period'),
        'channel_partner_code': row.get('channel partner code'),
    }

    if 'is active' in row:
        scheme_data['is_active'] = parse_bool(row.get('is active'))

    # AMFI Code mapping
    if 'amfi code' in row:
        scheme_data['amfi_code'] = row.get('amfi code')

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
    Parses a generic CSV/Excel for NAV history.
    Expected Columns: Scheme Code, Date, NAV
    """
    count = 0
    errors = []

    try:
        rows = read_file_to_dicts(file_obj)

        # Identify columns
        if not rows:
            return 0, []

        cols = rows[0].keys()
        scheme_col = next((c for c in cols if 'scheme' in c and 'code' in c), None)
        date_col = next((c for c in cols if 'date' in c), None)
        nav_col = next((c for c in cols if 'nav' in c or 'value' in c), None)

        if not (scheme_col and date_col and nav_col):
            return 0, [f"Missing required columns. Found: {list(cols)}"]

        new_navs = []
        BATCH_SIZE = 1000

        for row_idx, row in enumerate(rows, start=1):
            try:
                s_code = str(row[scheme_col]).strip()
                date_val = row[date_col]
                nav_val = row[nav_col]

                if not (s_code and date_val and nav_val):
                    continue

                # Find Scheme
                scheme = Scheme.objects.filter(scheme_code=s_code).first()
                if not scheme:
                    scheme = Scheme.objects.filter(rta_scheme_code=s_code).first()

                if not scheme:
                    errors.append(f"Row {row_idx}: Scheme not found for code {s_code}")
                    continue

                # Parse Date
                parsed_date = None
                if isinstance(date_val, (datetime, pd.Timestamp)):
                    parsed_date = date_val.date()
                else:
                    date_str = str(date_val).strip()
                    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
                        try:
                            parsed_date = datetime.strptime(date_str, fmt).date()
                            break
                        except ValueError:
                            continue

                if not parsed_date:
                    errors.append(f"Row {row_idx}: Invalid date format {date_val}")
                    continue

                # Parse NAV
                try:
                    nav_decimal = Decimal(str(nav_val))
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
