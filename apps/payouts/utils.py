import pandas as pd
import datetime
from decimal import Decimal
from simpledbf import Dbf5
import os
from django.conf import settings
from django.utils import timezone
from .models import BrokerageTransaction, Payout, DistributorCategory
from apps.users.models import DistributorProfile, InvestorProfile
from apps.reconciliation.models import Holding
from apps.products.models import Scheme
from django.db.models import Sum, Q

def process_brokerage_import(brokerage_import):
    """
    Main entry point for processing an uploaded BrokerageImport.
    """
    brokerage_import.status = brokerage_import.STATUS_PROCESSING
    brokerage_import.save()

    try:
        # Pre-fetch Schemes and Distributors to optimize lookups
        scheme_map, distributor_map = prefetch_mapping_data()

        # 1. Process CAMS File
        if brokerage_import.cams_file:
            process_cams_file(brokerage_import, scheme_map, distributor_map)

        # 2. Process Karvy File
        if brokerage_import.karvy_file:
            process_karvy_file(brokerage_import, scheme_map, distributor_map)

        # 3. Calculate Payouts
        calculate_payouts(brokerage_import)

        brokerage_import.status = brokerage_import.STATUS_COMPLETED
        brokerage_import.processed_at = timezone.now()
        brokerage_import.save()

    except Exception as e:
        brokerage_import.status = brokerage_import.STATUS_FAILED
        brokerage_import.error_log = str(e)
        brokerage_import.save()
        raise e

def prefetch_mapping_data():
    """
    Fetches all Schemes and Distributors into memory for fast lookup.
    """
    # Scheme Map: {(rta_code, amc_code, scheme_code) -> Scheme}
    # Since we look up by any of these, we can build a combined lookup strategy.
    # To save memory, we'll store multiple keys pointing to the same object.

    schemes = Scheme.objects.all()
    scheme_map = {}
    for s in schemes:
        if s.rta_scheme_code:
            scheme_map[s.rta_scheme_code.strip().upper()] = s
        if s.amc_scheme_code:
            scheme_map[s.amc_scheme_code.strip().upper()] = s
        if s.scheme_code:
            scheme_map[s.scheme_code.strip().upper()] = s

    # Distributor Map: {broker_code -> Distributor}
    # Also include old_broker_code
    distributors = DistributorProfile.objects.all()
    distributor_map = {}
    for d in distributors:
        if d.broker_code:
            distributor_map[d.broker_code.strip().upper()] = d
        if d.old_broker_code:
            distributor_map[d.old_broker_code.strip().upper()] = d

    return scheme_map, distributor_map

def process_cams_file(brokerage_import, scheme_map, distributor_map):
    file_path = brokerage_import.cams_file.path

    # Check file extension
    if file_path.lower().endswith('.dbf'):
        dbf = Dbf5(file_path)
        df = dbf.to_dataframe()
    else:
        # Assuming CSV if not DBF (rare for CAMS standard, but good fallback)
        df = pd.read_csv(file_path)

    # Standard CAMS columns often include:
    # BROK_CODE, BRKAGE_AMT, INV_NAME, FOLIO_NO, SCHEME_COD, TRXN_TYPE, PROC_DATE
    # Note: Column names in DBF are often truncated to 10 chars.

    transactions = []

    # Iterate through rows
    for _, row in df.iterrows():
        # Clean Row Data
        data = clean_pandas_data(row.to_dict())

        # Extract Key Fields (Handle variations in column names if necessary)
        brokerage = get_safe_decimal(row.get('BRKAGE_AMT', 0))
        amount = get_safe_decimal(row.get('PLOT_AMOUN', 0))

        # Date Handling
        raw_date = row.get('TRXN_DATE', row.get('PROC_DATE'))
        txn_date = None

        if pd.notna(raw_date):
            try:
                dt = pd.to_datetime(raw_date)
                if not pd.isna(dt):
                    txn_date = dt.date()
            except (ValueError, TypeError):
                txn_date = None

        # Scheme Determination
        scheme_code_raw = str(row.get('SCHEME_COD', '')).strip().upper()
        scheme = scheme_map.get(scheme_code_raw)

        # Distributor Mapping Logic (In-Memory)
        distributor = None
        is_mapped = False
        mapping_remark = "No Sub-Broker Code found"

        # Keys to look for (Normalized to Upper)
        # CAMS: subbrok -> SUBBROK
        # Karvy: Sub-Broker -> SUB-BROKER, td_broker -> TD_BROKER, TD_AGENT -> TD_AGENT
        keys_to_check = ['AE_CODE', 'SUB-BROKER', 'SUBBROK']

        # Normalize keys in row to uppercase for easier lookup
        row_upper = {str(k).upper().strip(): v for k, v in data.items()}

        sub_broker_code = None
        for key in keys_to_check:
            val = row_upper.get(key)
            if val:
                val_str = str(val).strip()
                if val_str and val_str.lower() not in ['nan', 'none', '']:
                    sub_broker_code = val_str
                    break

        if sub_broker_code:
            distributor = distributor_map.get(sub_broker_code.upper())
            if distributor:
                is_mapped = True
                mapping_remark = f"Mapped via Sub-Broker Code {sub_broker_code}"
            else:
                mapping_remark = f"Sub-Broker Code {sub_broker_code} not found"

        transaction = BrokerageTransaction(
            import_file=brokerage_import,
            source=BrokerageTransaction.SOURCE_CAMS,
            transaction_date=txn_date,
            investor_name=row.get('INV_NAME', ''),
            folio_number=row.get('FOLIO_NO', ''),
            scheme_name=row.get('SCHEME_NAM', row.get('SCHEME_COD', '')),
            scheme=scheme,
            amount=amount,
            brokerage_amount=brokerage,
            distributor=distributor,
            is_mapped=is_mapped,
            mapping_remark=mapping_remark,
            raw_data=data
        )

        transactions.append(transaction)

    # Batch Insert
    BrokerageTransaction.objects.bulk_create(transactions, batch_size=1000)

def process_karvy_file(brokerage_import, scheme_map, distributor_map):
    file_path = brokerage_import.karvy_file.path
    df = pd.read_csv(file_path)

    # Karvy CSV often has: 'Broker Code', 'Brokerage (in Rs.)', 'Transaction Date', 'Investor Name'

    transactions = []
    for _, row in df.iterrows():
        data = clean_pandas_data(row.to_dict())

        brokerage = get_safe_decimal(row.get('Brokerage (in Rs.)', 0))
        amount = get_safe_decimal(row.get('Amount (in Rs.)', 0))

        # Karvy Date format often DD/MM/YYYY
        txn_date_str = row.get('Transaction Date', row.get('Process Date'))
        txn_date = None
        if pd.notna(txn_date_str):
            try:
                dt = pd.to_datetime(txn_date_str, dayfirst=True)
                if not pd.isna(dt):
                    txn_date = dt.date()
            except (ValueError, TypeError):
                txn_date = None

        # Scheme Determination
        product_code_raw = str(row.get('Product Code', row.get('FMCODE', ''))).strip().upper()
        scheme = scheme_map.get(product_code_raw)

        # Distributor Mapping Logic (In-Memory)
        distributor = None
        is_mapped = False
        mapping_remark = "No Sub-Broker Code found"

        keys_to_check = ['AE_CODE', 'SUB-BROKER', 'SUBBROK']
        row_upper = {str(k).upper().strip(): v for k, v in data.items()}

        sub_broker_code = None
        for key in keys_to_check:
            val = row_upper.get(key)
            if val:
                val_str = str(val).strip()
                if val_str and val_str.lower() not in ['nan', 'none', '']:
                    sub_broker_code = val_str
                    break

        if sub_broker_code:
            distributor = distributor_map.get(sub_broker_code.upper())
            if distributor:
                is_mapped = True
                mapping_remark = f"Mapped via Sub-Broker Code {sub_broker_code}"
            else:
                mapping_remark = f"Sub-Broker Code {sub_broker_code} not found"

        transaction = BrokerageTransaction(
            import_file=brokerage_import,
            source=BrokerageTransaction.SOURCE_KARVY,
            transaction_date=txn_date,
            investor_name=row.get('Investor Name', ''),
            folio_number=str(row.get('Account Number', row.get('Folio Number', ''))),
            scheme_name=row.get('Fund Description', row.get('Scheme Name', '')),
            scheme=scheme,
            amount=amount,
            brokerage_amount=brokerage,
            distributor=distributor,
            is_mapped=is_mapped,
            mapping_remark=mapping_remark,
            raw_data=data
        )

        transactions.append(transaction)

    BrokerageTransaction.objects.bulk_create(transactions, batch_size=1000)


def reprocess_brokerage_import(brokerage_import):
    """
    Retries mapping for unmapped transactions and recalculates payouts.
    """
    # Optimized reprocessing: fetch map once, iterate objects, then bulk update
    _, distributor_map = prefetch_mapping_data()

    unmapped_transactions = BrokerageTransaction.objects.filter(
        import_file=brokerage_import,
        is_mapped=False
    )

    updated_txns = []
    mapped_count = 0

    for txn in unmapped_transactions:
        # Re-apply mapping logic
        raw_data = txn.raw_data
        if isinstance(raw_data, str):
            import ast
            try:
                raw_data = ast.literal_eval(raw_data)
            except:
                raw_data = {}

        row_upper = {str(k).upper().strip(): v for k, v in raw_data.items()}
        keys_to_check = ['AE_CODE', 'SUB-BROKER', 'SUBBROK']

        sub_broker_code = None
        for key in keys_to_check:
            val = row_upper.get(key)
            if val:
                val_str = str(val).strip()
                if val_str and val_str.lower() not in ['nan', 'none', '']:
                    sub_broker_code = val_str
                    break

        if sub_broker_code:
            distributor = distributor_map.get(sub_broker_code.upper())
            if distributor:
                txn.distributor = distributor
                txn.is_mapped = True
                txn.mapping_remark = f"Mapped via Sub-Broker Code {sub_broker_code}"
                updated_txns.append(txn)
                mapped_count += 1
            else:
                # Update remark even if still failed, to show we tried
                prev_remark = txn.mapping_remark
                new_remark = f"Sub-Broker Code {sub_broker_code} not found"
                if prev_remark != new_remark:
                    txn.mapping_remark = new_remark
                    updated_txns.append(txn)

    if updated_txns:
        BrokerageTransaction.objects.bulk_update(updated_txns, ['distributor', 'is_mapped', 'mapping_remark'], batch_size=1000)

    # Always recalculate payouts to reflect any changes
    calculate_payouts(brokerage_import)

    return mapped_count

def calculate_payouts(brokerage_import):
    """
    Aggregates transactions and calculates final payout based on AUM tiers.
    """
    # 0. Clear existing payouts for this import to avoid duplicates
    Payout.objects.filter(brokerage_import=brokerage_import).delete()

    # 1. Identify all distributors involved in this import
    # (We only care about transactions that were successfully mapped)
    distributor_ids = BrokerageTransaction.objects.filter(
        import_file=brokerage_import,
        is_mapped=True
    ).values_list('distributor_id', flat=True).distinct()

    payouts_to_create = []

    for dist_id in distributor_ids:
        distributor = DistributorProfile.objects.get(id=dist_id)

        # 2. Calculate Total AUM for this distributor (Live from Holdings)
        # Sum of current_value of all holdings linked to investors of this distributor
        total_aum = Holding.objects.filter(
            investor__distributor=distributor
        ).aggregate(Sum('current_value'))['current_value__sum'] or Decimal(0)

        # 3. Determine Category
        category = get_distributor_category(total_aum)
        share_percent = category.share_percentage if category else Decimal(0)
        category_name = category.name if category else "Uncategorized"

        # 4. Sum Brokerage from this Import
        gross_brokerage = BrokerageTransaction.objects.filter(
            import_file=brokerage_import,
            distributor=distributor
        ).aggregate(Sum('brokerage_amount'))['brokerage_amount__sum'] or Decimal(0)

        # 5. Calculate Payable
        payable = (gross_brokerage * share_percent) / Decimal(100)

        payout = Payout(
            brokerage_import=brokerage_import,
            distributor=distributor,
            total_aum=total_aum,
            category=category_name,
            share_percentage=share_percent,
            gross_brokerage=gross_brokerage,
            payable_amount=payable
        )
        payouts_to_create.append(payout)

    Payout.objects.bulk_create(payouts_to_create)

def clean_pandas_data(data):
    """
    Cleans a pandas-derived dictionary, converting non-serializable types to Python natives.
    """
    cleaned = {}
    for k, v in data.items():
        if pd.isna(v):
            cleaned[k] = None
        elif isinstance(v, (pd.Timestamp, datetime.datetime, datetime.date)):
             cleaned[k] = str(v)
        elif isinstance(v, (pd.Timedelta)):
             cleaned[k] = str(v)
        elif hasattr(v, 'item'): # numpy types like np.int64
             cleaned[k] = v.item()
        else:
             cleaned[k] = v
    return cleaned

def get_distributor_category(aum):
    """
    Returns the DistributorCategory object based on AUM.
    """
    # Logic: min_aum <= aum < max_aum
    # Ordered by min_aum descending to match highest tier first
    categories = DistributorCategory.objects.all().order_by('-min_aum')

    for cat in categories:
        if aum >= cat.min_aum:
            # If max_aum is None (Infinity) or aum is less than max_aum
            if cat.max_aum is None or aum < cat.max_aum:
                return cat
    return None

def get_safe_decimal(val):
    """
    Safely converts a value to Decimal, handling NaN and other invalid formats by returning 0.
    """
    if pd.isna(val) or val is None:
        return Decimal(0)

    try:
        s = str(val).strip()
        if not s or s.lower() == 'nan':
            return Decimal(0)
        d = Decimal(s)
        if d.is_nan():
            return Decimal(0)
        return d
    except (ValueError, TypeError, ArithmeticError):
        return Decimal(0)
