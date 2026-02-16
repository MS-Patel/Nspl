import pytest
from django.core.management import call_command
from django.contrib.auth import get_user_model
from apps.users.models import InvestorProfile, BankAccount
from apps.investments.models import Mandate
import os
import csv

User = get_user_model()

@pytest.fixture
def sample_clients_csv(tmp_path):
    # Create a dummy clients CSV
    file_path = tmp_path / "clients.csv"
    headers = [
        "Member Code","Client Code","Primary Holder First Name","Primary Holder Middle Name","Primary Holder Last Name",
        "Tax Status","Gender","Primary Holder DOB/Incorporation","Occupation Code","Holding Nature",
        "Primary Holder PAN","Email","Indian Mobile No.",
        "Address 1","Address 2","Address 3","City","State","Pincode","Country",
        "Account No 1","IFSC Code 1","Bank Name 1","Bank Branch 1","Account Type 1","Default Bank Flag 1",
        "Nominee 1 Name","Nominee 1 Relationship","Nominee 1 Applicable(%)","Nomination Opt","Nomination Authentication Mode"
    ]
    data = [
        "24637","TEST001","John","D","Doe","INDIVIDUAL","Male","01/01/1980","BUSINESS","SINGLE",
        "ABCDE1234F","john@example.com","9876543210",
        "123 Street","Apt 1","","Mumbai","Maharashtra","400001","India",
        "1234567890","SBIN0001234","SBI","Mumbai Main","SAVINGS","Y",
        "Jane Doe","SPOUSE","100","Y","Z"
    ]

    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerow(data)

    return str(file_path)

@pytest.fixture
def sample_mandates_csv(tmp_path):
    # Create a dummy mandates CSV
    file_path = tmp_path / "mandates.csv"
    headers = [
        "MANDATE CODE","CLIENT CODE","CLIENT NAME","MEMBER CODE","BANK NAME","BANK BRANCH","AMOUNT",
        "REGN DATE","STATUS","UMRN NO","REMARKS","APPROVED DATE","BANK ACCOUNT NUMBER",
        "MANDATE COLLECTION TYPE","MANDATE TYPE","DATE OF UPLOAD","START DATE","END DATE"
    ]
    data = [
        "MAND001","TEST001","John Doe","24637","SBI","Mumbai Main","5000",
        "01/01/2023","APPROVED","","","","1234567890",
        "","E-MANDATE","","01/01/2023","31/12/2099"
    ]

    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerow(data)

    return str(file_path)

@pytest.mark.django_db
def test_import_command(sample_clients_csv, sample_mandates_csv):
    # Run command
    call_command('import_old_bse_data', clients_file=sample_clients_csv, mandates_file=sample_mandates_csv)

    # Check User
    user = User.objects.get(username="ABCDE1234F")
    assert user.email == "john@example.com"
    assert user.check_password("ABCDE1234F")

    # Check Profile
    profile = InvestorProfile.objects.get(user=user)
    assert profile.pan == "ABCDE1234F"
    assert profile.tax_status == InvestorProfile.INDIVIDUAL
    assert profile.city == "Mumbai"
    assert profile.nominees.count() == 1
    assert profile.nominees.first().name == "Jane Doe"

    # Check Bank Account
    bank = BankAccount.objects.get(investor=profile)
    assert bank.account_number == "1234567890"
    assert bank.is_default is True

    # Check Mandate
    mandate = Mandate.objects.get(mandate_id="MAND001")
    assert mandate.investor == profile
    assert mandate.amount_limit == 5000.0
    assert mandate.status == Mandate.APPROVED
