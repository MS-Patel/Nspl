import pandas as pd
from decimal import Decimal
from simpledbf import Dbf5
import os
from django.conf import settings
from django.utils import timezone
from .models import BrokerageTransaction, Payout, DistributorCategory
from apps.users.models import DistributorProfile, InvestorProfile
from apps.reconciliation.models import Holding
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
        data = row.to_dict()

        # Extract Key Fields (Handle variations in column names if necessary)
        brokerage = Decimal(str(row.get('BRKAGE_AMT', 0) or 0))
        amount = Decimal(str(row.get('PLOT_AMOUN', 0) or 0))
        txn_date = pd.to_datetime(row.get('TRXN_DATE', row.get('PROC_DATE'))) if row.get('TRXN_DATE') or row.get('PROC_DATE') else None

        if txn_date:
            txn_date = txn_date.date()

        transaction = BrokerageTransaction(
            import_file=brokerage_import,
            source=BrokerageTransaction.SOURCE_CAMS,
            transaction_date=txn_date,
            investor_name=row.get('INV_NAME', ''),
            folio_number=row.get('FOLIO_NO', ''),
            scheme_name=row.get('SCHEME_NAM', row.get('SCHEME_COD', '')), # Sometimes SCHEME_COD is a code
            amount=amount,
            brokerage_amount=brokerage,
            raw_data=str(data)
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
        data = row.to_dict()

        brokerage = Decimal(str(row.get('Brokerage (in Rs.)', 0) or 0))
        amount = Decimal(str(row.get('Amount (in Rs.)', 0) or 0))

        # Karvy Date format often DD/MM/YYYY
        txn_date_str = row.get('Transaction Date', row.get('Process Date'))
        txn_date = None
        if txn_date_str:
            try:
                txn_date = pd.to_datetime(txn_date_str, dayfirst=True).date()
            except:
                pass

        transaction = BrokerageTransaction(
            import_file=brokerage_import,
            source=BrokerageTransaction.SOURCE_KARVY,
            transaction_date=txn_date,
            investor_name=row.get('Investor Name', ''),
            folio_number=str(row.get('Account Number', row.get('Folio Number', ''))),
            scheme_name=row.get('Fund Description', row.get('Scheme Name', '')),
            amount=amount,
            brokerage_amount=brokerage,
            raw_data=str(data)
        )

        map_transaction(transaction)
        transactions.append(transaction)

    BrokerageTransaction.objects.bulk_create(transactions)

def map_transaction(transaction):
    """
    Logic to link a transaction to a DistributorProfile.
    """
    mapped = False

    # 1. Map via Sub-Broker Code (if present in raw data)
    # CAMS: SUB_BRK_CO / SUB_BRK_AR
    # Karvy: Sub-Broker Code

    # We need to parse raw_data back from string or pass it in.
    # For simplicity, let's assume we look at specific known fields.
    # Note: In `bulk_create`, `save()` isn't called, so this logic runs before bulk_create object construction.

    # (Since I'm doing bulk_create, I'm setting attributes on the object instance)

    # Logic:
    # Find Distributor by PAN (via Investor) or ARN

    distributor = None

    # Try 1: Folio Number Mapping
    # We check if we have this Folio mapped to an Investor in our system.
    if transaction.folio_number:
        # Clean folio
        folio = str(transaction.folio_number).strip()
        # Find Investor with this folio in Holdings (most reliable link)
        # OR check InvestorProfile -> but InvestorProfile doesn't store Folio directly (Holding does).
        # But we can try to find an investor via PAN if available in file.

        # Let's search Holdings first.
        holding = Holding.objects.filter(folio_number=folio).select_related('investor__distributor').first()
        if holding and holding.investor.distributor:
            distributor = holding.investor.distributor
            transaction.mapping_remark = f"Mapped via Folio {folio}"
            mapped = True

    # Try 2: Investor PAN (if available in file)
    # Karvy: 'InvPAN'
    # CAMS: 'PAN_NO'
    if not mapped:
        import ast
        try:
            raw = ast.literal_eval(transaction.raw_data) if isinstance(transaction.raw_data, str) else transaction.raw_data
            pan = raw.get('InvPAN', raw.get('PAN_NO', raw.get('PAN_NUMBER', '')))
            if pan:
                investor = InvestorProfile.objects.filter(pan=pan).select_related('distributor').first()
                if investor and investor.distributor:
                    distributor = investor.distributor
                    transaction.mapping_remark = f"Mapped via Investor PAN {pan}"
                    mapped = True
        except:
            pass

    if mapped and distributor:
        transaction.distributor = distributor
        transaction.is_mapped = True

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
