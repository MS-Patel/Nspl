from apps.reconciliation.models import Transaction
from apps.reconciliation.parsers import CAMSXLSParser, KarvyXLSParser
from apps.products.models import Scheme, AMC
from decimal import Decimal

def create_dummy_data():
    amc, _ = AMC.objects.get_or_create(name="Dummy AMC", code="DUMMY")
    Scheme.objects.get_or_create(scheme_code="FTI038", defaults={'amc': amc, 'name': "CAMS Scheme"})
    Scheme.objects.get_or_create(scheme_code="128TSGP", defaults={'amc': amc, 'name': "Karvy Scheme"})

def test_cams_fingerprint():
    print("Testing CAMS Fingerprint...")
    txn_no_prefix = "220265247"
    # Clean up
    Transaction.objects.filter(txn_number__startswith=txn_no_prefix).delete()

    try:
        parser = CAMSXLSParser(file_path="docs/rta/small_cams.xlsx")
        parser.parse()
    except Exception as e:
        print(f"Parser error: {e}")
        return

    # Check for fingerprinted transactions
    txns = Transaction.objects.filter(txn_number__startswith=txn_no_prefix)
    print(f"Found {txns.count()} transactions for {txn_no_prefix}")
    for txn in txns:
        print(f"  ID: {txn.txn_number} | Amount: {txn.amount} | Units: {txn.units}")

def test_karvy_fingerprint():
    print("\nTesting Karvy Fingerprint...")
    txn_no_prefix = "682020979"
    # Clean up
    Transaction.objects.filter(txn_number__startswith=txn_no_prefix).delete()

    try:
        parser = KarvyXLSParser(file_path="docs/rta/small_karvy.xlsx")
        parser.parse()
    except Exception as e:
        print(f"Parser error: {e}")
        return

    txns = Transaction.objects.filter(txn_number__startswith=txn_no_prefix)
    print(f"Found {txns.count()} transactions for {txn_no_prefix}")
    for txn in txns:
        print(f"  ID: {txn.txn_number} | Amount: {txn.amount} | Units: {txn.units}")

create_dummy_data()
test_cams_fingerprint()
test_karvy_fingerprint()
