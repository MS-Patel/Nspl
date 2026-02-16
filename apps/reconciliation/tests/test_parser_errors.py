import os
import pandas as pd
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from apps.users.models import InvestorProfile
from apps.products.models import Scheme, AMC
from apps.reconciliation.models import RTAFile, Transaction
from apps.reconciliation.parsers import CAMSXLSParser
from django.conf import settings

User = get_user_model()

@pytest.mark.django_db
def test_cams_xls_parser_error_handling_and_recovery(tmp_path):
    # Setup Data
    amc = AMC.objects.create(name="Test AMC", code="TAMC")
    scheme = Scheme.objects.create(
        amc=amc, scheme_code="VALID123", name="Valid Scheme",
        isin="INF123456789", scheme_plan="Regular", scheme_type="Growth"
    )

    # Scenario 1: User exists, Profile exists, but PAN mismatch (or lookup by PAN fails)
    # This simulates the "duplicate key" error condition
    user = User.objects.create_user(username="TESTPAN123", password="password")
    # Profile has different PAN or is just linked
    profile = InvestorProfile.objects.create(
        user=user, pan="OTHERPAN", firstname="Existing", lastname="User"
    )

    # Scenario 2: Row with invalid scheme (Should generate error)

    # Create Excel File
    data = [
        {
            # Row 1: Should match existing user/profile despite PAN lookup failure (because we fallback to user)
            "pan": "TESTPAN123",
            "inv_name": "Test User",
            "prodcode": "VALID123",
            "folio_no": "FOLIO1",
            "trxnno": "TXN1",
            "traddate": "2023-01-01",
            "amount": 1000,
            "units": 10,
            "trxntype": "P"
        },
        {
            # Row 2: Invalid Scheme (Should go to error file)
            "pan": "NEWPAN456",
            "inv_name": "New User",
            "prodcode": "INVALID999",
            "folio_no": "FOLIO2",
            "trxnno": "TXN2",
            "traddate": "2023-01-01",
            "amount": 2000,
            "units": 20,
            "trxntype": "P"
        }
    ]

    df = pd.DataFrame(data)
    file_path = tmp_path / "cams_test.xlsx"
    df.to_excel(file_path, index=False)

    # Create RTAFile object
    with open(file_path, 'rb') as f:
        rta_file = RTAFile.objects.create(
            rta_type=RTAFile.RTA_CAMS,
            file_name="cams_test.xlsx",
            file=SimpleUploadedFile("cams_test.xlsx", f.read())
        )

    # Initialize Parser
    # We need to point the parser to the temporary file we created because
    # RTAFile.file.path might not work easily in test environment with storage
    # But CAMSXLSParser uses self.file_path if provided.
    parser = CAMSXLSParser(rta_file, file_path=str(file_path))

    # Parse
    parser.parse()

    # Assertions

    # 1. Check Transaction for Row 1
    txn1 = Transaction.objects.filter(txn_number="TXN1").first()
    assert txn1 is not None
    assert txn1.scheme == scheme
    # It should have linked to the existing profile
    assert txn1.investor == profile

    # 2. Check Error File
    rta_file.refresh_from_db()
    assert rta_file.error_file is not None
    assert bool(rta_file.error_file) is True

    # Validate Error File Content
    # We can read the error file using pandas
    error_df = pd.read_excel(rta_file.error_file.path)

    # Expecting 1 error row
    assert len(error_df) == 1
    error_row = error_df.iloc[0]
    assert error_row['prodcode'] == "INVALID999"
    assert "Scheme not found" in error_row['error']

    # Cleanup (Optional, tmp_path handles file, Django handles DB)
