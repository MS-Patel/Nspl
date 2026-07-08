import csv
from datetime import date

import pytest
from django.core.management import call_command

from apps.investments.factories import MandateFactory, SIPFactory
from apps.products.factories import SchemeFactory
from apps.users.factories import (
    BankAccountFactory,
    DistributorProfileFactory,
    InvestorProfileFactory,
    NomineeFactory,
    RMProfileFactory,
)
from apps.users.models import Branch


def read_csv_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as file_obj:
        return list(csv.DictReader(file_obj))


@pytest.mark.django_db
def test_export_new_portal_imports_command_writes_expected_csvs(tmp_path):
    branch = Branch.objects.create(
        name="Ahmedabad Main",
        code="AMD-HQ",
        city="Ahmedabad",
        state="Gujarat",
        pincode="380001",
    )
    rm = RMProfileFactory(
        branch=branch,
        user__name="Primary RM",
        user__email="rm@example.com",
        employee_code="RM001",
        mobile="9876543210",
        city="Ahmedabad",
        state="Gujarat",
        pincode="380001",
        address="CG Road",
        pan="ABCDE1234F",
        alternate_mobile="9876543211",
        alternate_email="rm.alt@example.com",
        gstin="24ABCDE1234F1Z5",
        bank_name="HDFC Bank",
        account_number="00112233445566",
        ifsc_code="HDFC0000123",
        branch_name="Ahmedabad Main",
    )
    distributor = DistributorProfileFactory(
        user__name="Distributor Partner",
        user__email="dist@example.com",
        rm=rm,
        broker_code="DIST001",
        old_broker_code="SB001",
        arn_number="ARN001",
        euin="E123456",
        mobile="9988776655",
        city="Ahmedabad",
        state="Gujarat",
        pincode="380001",
        address="Ashram Road",
        pan="ABCDE2222F",
        alternate_mobile="9988776654",
        alternate_email="dist.alt@example.com",
        gstin="24ABCDE2222F1Z5",
        bank_name="ICICI Bank",
        account_number="99887766554433",
        ifsc_code="ICIC0000456",
        branch_name="Ahmedabad Branch",
        is_approved=True,
    )
    investor = InvestorProfileFactory(
        distributor=distributor,
        rm=rm,
        branch=branch,
        firstname="Aarav",
        middlename="",
        lastname="Shah",
        pan="ABCDE1234G",
        dob=date(1990, 1, 1),
        ucc_code="UCC10001",
        email="aarav.shah@example.com",
        mobile="9876543200",
        address_1="CG Road",
        city="Ahmedabad",
        state="Gujarat",
        pincode="380001",
        country="India",
        country_of_birth="India",
        place_of_birth="Ahmedabad",
        second_applicant_name="Riya Shah",
        second_applicant_pan="ABCDE2345F",
        guardian_name="Mahesh Shah",
        guardian_pan="ABCDE3456F",
    )
    bank_account = BankAccountFactory(
        investor=investor,
        account_number="123456789012",
        bank_name="HDFC Bank",
        branch_name="Ahmedabad Main",
        ifsc_code="HDFC0000123",
        account_type="SB",
        is_default=True,
    )
    NomineeFactory(
        investor=investor,
        name="Meera Shah",
        relationship="Spouse",
        percentage=100,
        guardian_name="",
    )
    mandate = MandateFactory(
        investor=investor,
        bank_account=bank_account,
        mandate_id="MAND10001",
        amount_limit="100000",
        mandate_type="X",
    )
    scheme = SchemeFactory(isin="INF000000001", scheme_code="SCH12345")
    SIPFactory(
        investor=investor,
        scheme=scheme,
        mandate=mandate,
        amount="5000",
        frequency="MONTHLY",
        start_date=date(2024, 2, 1),
        installments=120,
        status="ACTIVE",
        bse_reg_no="SIP10001",
    )

    output_dir = tmp_path / "exports"
    call_command(
        "export_new_portal_imports",
        output_dir=str(output_dir),
        member_code="24637",
    )

    rm_rows = read_csv_rows(output_dir / "rm_bulk_import.csv")
    assert rm_rows == [{
        "name": "Primary RM",
        "email": "rm@example.com",
        "mobile": "9876543210",
        "employee_code": "RM001",
        "branch_code": "AMD-HQ",
        "active": "Yes",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "pincode": "380001",
        "address": "CG Road",
        "pan": "ABCDE1234F",
        "alternate_mobile": "9876543211",
        "alternate_email": "rm.alt@example.com",
        "dob": "",
        "gstin": "24ABCDE1234F1Z5",
        "bank_name": "HDFC Bank",
        "account_number": "00112233445566",
        "ifsc_code": "HDFC0000123",
        "branch_name": "Ahmedabad Main",
        "country": "India",
    }]

    distributor_rows = read_csv_rows(output_dir / "distributor_bulk_import.csv")
    assert distributor_rows == [{
        "name": "Distributor Partner",
        "email": "dist@example.com",
        "mobile": "9988776655",
        "distributor_code": "DIST001",
        "branch_code": "AMD-HQ",
        "rm_employee_code": "RM001",
        "active": "Yes",
        "is_approved": "Yes",
        "arn_code": "ARN001",
        "subbroker_code": "SB001",
        "euin_code": "E123456",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "pincode": "380001",
        "address": "Ashram Road",
        "pan": "ABCDE2222F",
        "alternate_mobile": "9988776654",
        "alternate_email": "dist.alt@example.com",
        "dob": "",
        "gstin": "24ABCDE2222F1Z5",
        "bank_name": "ICICI Bank",
        "account_number": "99887766554433",
        "ifsc_code": "ICIC0000456",
        "branch_name": "Ahmedabad Branch",
        "country": "India",
    }]

    investor_rows = read_csv_rows(output_dir / "investor_client-master.csv")
    assert investor_rows == [{
        "Member Code": "24637",
        "Client Code": "UCC10001",
        "Primary Holder First Name": "Aarav",
        "Primary Holder Middle Name": "",
        "Primary Holder Last Name": "Shah",
        "Tax Status": "INDIVIDUAL",
        "Primary Holder DOB/Incorporation": investor.dob.isoformat(),
        "Occupation Code": "SERVICE",
        "Holding Nature": "SINGLE",
        "Primary Holder PAN": "ABCDE1234G",
        "Email": "aarav.shah@example.com",
        "Indian Mobile No.": "9876543200",
        "Address 1": "CG Road",
        "Address 2": "",
        "Address 3": "",
        "City": "Ahmedabad",
        "State": "Gujarat",
        "Pincode": "380001",
        "Country": "India",
        "Second Holder First Name": "Riya",
        "Second Holder Middle Name": "",
        "Second Holder Last Name": "Shah",
        "Second Holder PAN": "ABCDE2345F",
        "Third Holder First Name": "",
        "Third Holder Middle Name": "",
        "Third Holder Last Name": "",
        "Third Holder PAN": "",
        "Guardian First Name": "Mahesh",
        "Guardian Middle Name": "",
        "Guardian Last Name": "Shah",
        "Guardian PAN": "ABCDE3456F",
        "Account No 1": "123456789012",
        "Bank Name 1": "HDFC Bank",
        "Bank Branch 1": "Ahmedabad Main",
        "IFSC Code 1": "HDFC0000123",
        "Account Type 1": "SAVINGS",
        "Default Bank Flag 1": "Y",
        "Nominee 1 Name": "Meera Shah",
        "Nominee 1 %": "100",
        "Nominee 1 Relationship": "Spouse",
        "Nominee 1 DOB": "",
        "Nominee 1 Guardian": "",
    }]

    fatca_rows = read_csv_rows(output_dir / "investor_fatca.csv")
    assert fatca_rows == [{
        "PAN_RP": "ABCDE1234G",
        "CO_BIR_INC": "India",
        "PO_BIR_INC": "Ahmedabad",
        "TAX_RES1": "India",
        "OCC_CODE": "SERVICE",
        "SRCE_WEALT": "Salary",
        "INC_SLAB": "1-5L",
        "PEP_FLAG": "N",
        "SrNo": f"FATCA-{investor.pk:05d}",
    }]

    mandate_rows = read_csv_rows(output_dir / "investor_mandates.csv")
    assert mandate_rows == [{
        "MANDATE CODE": "MAND10001",
        "CLIENT CODE": "UCC10001",
        "BANK ACCOUNT NUMBER": "123456789012",
        "BANK NAME": "HDFC Bank",
        "BANK BRANCH": "Ahmedabad Main",
        "STATUS": "APPROVED",
        "MANDATE TYPE": "XSP",
        "AMOUNT": "100000",
        "START DATE": mandate.start_date.isoformat(),
        "END DATE": "",
        "REGN DATE": mandate.created_at.date().isoformat(),
        "APPROVED DATE": mandate.updated_at.date().isoformat(),
        "UMRN NO": "MAND10001",
        "REMARKS": "",
    }]

    sip_rows = read_csv_rows(output_dir / "investor_sips.csv")
    assert sip_rows == [{
        "SIP Registration Number": "SIP10001",
        "PAN": "ABCDE1234G",
        "Client Code": "UCC10001",
        "Scheme Code": "INF000000001",
        "Mandate Code": "MAND10001",
        "Amount": "5000",
        "Frequency": "MONTHLY",
        "Start Date": "2024-02-01",
        "End Date": "",
        "Installments": "120",
        "Status": "ACTIVE",
        "Folio Number": "",
    }]
