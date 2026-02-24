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
from django.db.models import Sum

def process_brokerage_import(brokerage_import):
    """
    Main entry point for processing an uploaded BrokerageImport.
    """
    brokerage_import.status = brokerage_import.STATUS_PROCESSING
    brokerage_import.save()

    try:
        # 1. Process CAMS File
        if brokerage_import.cams_file:
            process_cams_file(brokerage_import)

        # 2. Process Karvy File
        if brokerage_import.karvy_file:
            process_karvy_file(brokerage_import)

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

def process_cams_file(brokerage_import):
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

    # We iterate and save raw transactions
    transactions = []
    for _, row in df.iterrows():
        # Clean Row Data
        data = clean_pandas_data(row.to_dict())

        # Extract Key Fields (Handle variations in column names if necessary)
        brokerage = get_safe_decimal(row.get('BRKAGE_AMT', 0))
        amount = get_safe_decimal(row.get('PLOT_AMOUN', 0))
        txn_date = pd.to_datetime(row.get('TRXN_DATE', row.get('PROC_DATE'))) if row.get('TRXN_DATE') or row.get('PROC_DATE') else None

        if txn_date:
            txn_date = txn_date.date()
        # Scheme Determination
        scheme_code = str(row.get('SCHEME_COD', '')).strip()
        scheme = None
        if scheme_code:
            scheme = Scheme.objects.filter(channel_partner_code=scheme_code).first()
            if not scheme:
                scheme = Scheme.objects.filter(rta_scheme_code=scheme_code).first()
            if not scheme:
                scheme = Scheme.objects.filter(scheme_code=scheme_code).first()

        transaction = BrokerageTransaction(
            import_file=brokerage_import,
            source=BrokerageTransaction.SOURCE_CAMS,
            transaction_date=txn_date,
            investor_name=row.get('INV_NAME', ''),
            folio_number=row.get('FOLIO_NO', ''),
            scheme_name=row.get('SCHEME_NAM', row.get('SCHEME_COD', '')), # Sometimes SCHEME_COD is a code
            scheme=scheme,
            amount=amount,
            brokerage_amount=brokerage,
            raw_data=data
        )

        # Attempt Mapping
        map_transaction(transaction)
        transactions.append(transaction)

    BrokerageTransaction.objects.bulk_create(transactions)

def process_karvy_file(brokerage_import):
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
        if txn_date_str:
            try:
                txn_date = pd.to_datetime(txn_date_str, dayfirst=True).date()
            except:
                pass
        # Scheme Determination
        product_code = str(row.get('Product Code', '')).strip()
        scheme = None
        if product_code:
            scheme = Scheme.objects.filter(channel_partner_code=product_code).first()
            if not scheme:
                scheme = Scheme.objects.filter(rta_scheme_code=product_code).first()
            if not scheme:
                scheme = Scheme.objects.filter(scheme_code=product_code).first()

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
            raw_data=data
        )

        map_transaction(transaction)
        transactions.append(transaction)

    BrokerageTransaction.objects.bulk_create(transactions)

def map_transaction(transaction):
    """
    Logic to link a transaction to a DistributorProfile.
    Mapping is now strictly based on Sub-Broker Code matching.
    """
    import ast

    transaction.is_mapped = False
    transaction.distributor = None

    try:
        raw = ast.literal_eval(transaction.raw_data) if isinstance(transaction.raw_data, str) else transaction.raw_data

        # Normalize keys to uppercase for easier lookup
        # raw keys might be mixed case
        raw_upper = {str(k).upper().strip(): v for k, v in raw.items()}

        # Keys to look for (Normalized to Upper)
        # CAMS: subbrok -> SUBBROK
        # Karvy: Sub-Broker -> SUB-BROKER, td_broker -> TD_BROKER, TD_AGENT -> TD_AGENT

        keys_to_check = ['AE_CODE', 'SUB-BROKER']

        sub_broker_code = None
        for key in keys_to_check:
            val = raw_upper.get(key)
            if val:
                val_str = str(val).strip()
                if val_str and val_str.lower() not in ['nan', 'none', '']:
                    sub_broker_code = val_str
                    break

        if sub_broker_code:
            # Match against DistributorProfile.broker_code (Case Insensitive)
            distributor = DistributorProfile.objects.filter(broker_code__iexact=sub_broker_code).first()

            # If not found, try matching against old_broker_code
            if not distributor:
                distributor = DistributorProfile.objects.filter(old_broker_code__iexact=sub_broker_code).first()

            if distributor:
                transaction.distributor = distributor
                transaction.is_mapped = True
                transaction.mapping_remark = f"Mapped via Sub-Broker Code {sub_broker_code}"
            else:
                transaction.mapping_remark = f"Sub-Broker Code {sub_broker_code} not found"
        else:
            transaction.mapping_remark = "No Sub-Broker Code found"

    except Exception as e:
        transaction.mapping_remark = f"Error during mapping: {str(e)}"

def reprocess_brokerage_import(brokerage_import):
    """
    Retries mapping for unmapped transactions and recalculates payouts.
    """
    unmapped_transactions = BrokerageTransaction.objects.filter(
        import_file=brokerage_import,
        is_mapped=False
    )

    mapped_count = 0
    for txn in unmapped_transactions:
        # map_transaction modifies the object in-place
        map_transaction(txn)
        if txn.is_mapped:
            txn.save()
            mapped_count += 1

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
