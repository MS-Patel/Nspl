import pytest
import os
import shutil
from decimal import Decimal
from django.conf import settings
from apps.reconciliation.utils.parser_registry import get_parser_for_file
from apps.reconciliation.models import Transaction, RTAFile
from apps.products.models import Scheme, AMC
from apps.users.models import InvestorProfile

@pytest.fixture
def sample_mfsd307_csv(tmp_path):
    # Path to the sample file in the repo
    source_path = os.path.join(settings.BASE_DIR, 'docs', 'rta', 'MFSD307_WBTRN19371298_882696.csv')

    # Create a temp file with the same name to trigger the detector
    dest_path = tmp_path / "MFSD307_WBTRN19371298_882696.csv"
    shutil.copy(source_path, dest_path)

    return str(dest_path)

@pytest.mark.django_db
def test_karvy_mfsd307_parser_selection(sample_mfsd307_csv):
    """
    Tests that the MFSD307 CSV file is correctly identified and parsed.
    """
    # 1. Check Parser Selection
    parser = get_parser_for_file(sample_mfsd307_csv)
    assert parser is not None, "Parser should not be None"

    print(f"Selected Parser: {parser.__class__.__name__}")
    assert parser.__class__.__name__ == "KarvyMFSD307Parser"

    # 2. Setup Dependencies (Scheme, etc.)
    # The sample file has Scheme Code 'IORG' and 'MCGP'
    amc = AMC.objects.create(name="Mirae Asset", code="MIRAE")
    Scheme.objects.create(amc=amc, scheme_code="IORG", name="Mirae Asset Large Cap Fund")
    Scheme.objects.create(amc=amc, scheme_code="MCGP", name="Invesco India Midcap Fund")

    # 3. Parse
    try:
        parser.parse()
    except Exception as e:
        pytest.fail(f"Parsing failed: {e}")

    # 4. Verify Transactions
    # Check for a transaction from the file
    # Row 1: Folio 70114321916, Scheme IORG, Amount 437.45, Units 3.809, Type RED (Redemption)

    txn = Transaction.objects.filter(folio_number="70114321916", amount=437.45).first()
    assert txn is not None, "Transaction not found"
    assert txn.units == Decimal("3.809")
    assert txn.txn_type_code == "RED" # Based on SubTranType
    assert txn.rta_code == "KARVY"

    # Check another one (Systematic Investment)
    # Row 20: Purchase, P, NEW. Folio 138350276, Scheme SCGP (not created)
    # Let's check MCGP row (Row 17 in sample file approx)
    # 120MCGP, 30135577894, Amount 1499.93, Units 8.342, SubTranType SIN

    txn2 = Transaction.objects.filter(folio_number="30135577894", amount=1499.93).first()
    assert txn2 is not None, "Transaction 2 not found"
    assert txn2.units == Decimal("8.342")
    assert txn2.txn_type_code == "SIN"
