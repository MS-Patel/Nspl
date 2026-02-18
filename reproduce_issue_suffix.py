from apps.reconciliation.models import Transaction
from apps.reconciliation.parsers import CAMSXLSParser, KarvyXLSParser
from apps.products.models import Scheme, AMC
from decimal import Decimal

def create_dummy_data():
    amc, _ = AMC.objects.get_or_create(name="Dummy AMC", code="DUMMY")
    Scheme.objects.get_or_create(scheme_code="FTI038", defaults={'amc': amc, 'name': "CAMS Scheme"})
    Scheme.objects.get_or_create(scheme_code="128TSGP", defaults={'amc': amc, 'name': "Karvy Scheme"})

def test_cams_aggregation():
    print("Testing CAMS Suffixing...")
    txn_no = "220265247"
    # Clean up
    Transaction.objects.filter(txn_number__startswith=txn_no).delete()

    try:
        parser = CAMSXLSParser(file_path="docs/rta/small_cams.xlsx")
        parser.parse()
    except Exception as e:
        print(f"Parser error: {e}")
        return

    # Check for original
    txn1 = Transaction.objects.filter(txn_number=txn_no).first()
    if txn1:
        print(f"Txn {txn_no}: Amount={txn1.amount}, Units={txn1.units}")
    else:
        print(f"Txn {txn_no} not found")

    # Check for suffix
    txn2 = Transaction.objects.filter(txn_number=f"{txn_no}-2").first()
    if txn2:
        print(f"Txn {txn_no}-2: Amount={txn2.amount}, Units={txn2.units}")
    else:
        print(f"Txn {txn_no}-2 not found")

def test_karvy_aggregation():
    print("\nTesting Karvy Suffixing...")
    txn_no = "682020979"
    # Clean up
    Transaction.objects.filter(txn_number__startswith=txn_no).delete()

    try:
        parser = KarvyXLSParser(file_path="docs/rta/small_karvy.xlsx")
        parser.parse()
    except Exception as e:
        print(f"Parser error: {e}")
        return

    txn1 = Transaction.objects.filter(txn_number=txn_no).first()
    if txn1:
        print(f"Txn {txn_no}: Amount={txn1.amount}, Units={txn1.units}")

    txn2 = Transaction.objects.filter(txn_number=f"{txn_no}-2").first()
    if txn2:
        print(f"Txn {txn_no}-2: Amount={txn2.amount}, Units={txn2.units}")

create_dummy_data()
test_cams_aggregation()
test_karvy_aggregation()
