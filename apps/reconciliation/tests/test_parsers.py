import os
import pandas as pd
import io
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.reconciliation.models import RTAFile, Transaction, Holding
from apps.reconciliation.parsers import KarvyCSVParser, FranklinParser, DBFParser
from apps.users.models import InvestorProfile, User
from apps.products.models import Scheme, AMC, SchemeCategory
from datetime import date
from decimal import Decimal

class ParserTestBase(TestCase):
    def setUp(self):
        # Setup Master Data
        self.amc = AMC.objects.create(name="HDFC Mutual Fund", code="HDFC")
        self.category = SchemeCategory.objects.create(name="Equity")
        self.scheme = Scheme.objects.create(
            name="HDFC Top 100",
            scheme_code="HDFC100",
            channel_partner_code="HDFC100",
            rta_scheme_code="KARVY001",
            amc=self.amc,
            category=self.category,
            purchase_allowed=True
        )

        # Setup User/Investor
        self.user = User.objects.create_user(username="ABCDE1234F", email="test@example.com", user_type='INVESTOR', name="John Doe")
        self.investor = InvestorProfile.objects.create(
            user=self.user,
            pan="ABCDE1234F",
            email="test@example.com",
            mobile="9999999999"
        )

class FranklinParserTest(ParserTestBase):
    def test_franklin_parser(self):
        # Assuming FT Layout (Pipe):
        # 1: Scheme, 3: Folio, 5: Type, 6: TxnNo, 7: Units, 8: Amt, 9: Date, 18: PAN
        row_data = ["COMP", "HDFC100", "Name", "12345/F", "InvName", "P", "FTXN01", "25.0", "2500.00", "01-01-2024", "x", "x", "x", "x", "x", "x", "x", "x", "ABCDE1234F"]
        # Ensure row has enough columns
        while len(row_data) < 26: row_data.append("")

        file_content = "Header\n" + "|".join(row_data)
        uploaded_file = SimpleUploadedFile("franklin_feed.txt", file_content.encode('utf-8'))
        rta_file = RTAFile.objects.create(rta_type=RTAFile.RTA_FRANKLIN, file_name="ft.txt", file=uploaded_file)

        parser = FranklinParser(rta_file)
        parser.parse()

        self.assertEqual(rta_file.status, RTAFile.STATUS_PROCESSED)
        txn = Transaction.objects.get(txn_number="FTXN01")
        self.assertEqual(txn.units, Decimal("25.0"))
        self.assertEqual(txn.scheme, self.scheme)

class KarvyCSVParserTest(ParserTestBase):
    def test_karvy_csv_parser(self):
        # Prepare DataFrame mimicking Karvy CSV
        data = {
            'Product Code': ['KARVY001'],
            'Fund': ['FundName'],
            'Folio Number': ['12345/K'],
            'Scheme Code': ['HDFC100'],
            'Fund Description': ['HDFC Top 100'],
            'Transaction Head': ['P'],
            'Transaction Number': ['KTXN01'],
            'Switch_Ref. No.': [''],
            'Instrument Number': [''],
            'Investor Name': ['John Doe'],
            'Transaction Mode': ['P'],
            'Transaction Status': ['OK'],
            'Branch Name': ['Mumbai'],
            'Branch Transaction No': [''],
            'Transaction Date': ['01-Jan-2024'],
            'Process Date': ['02-Jan-2024'],
            'Price': ['100.00'],
            'Units': ['50.0'],
            'Amount': ['5000.00'],
            'Agent Code': [''],
            'Sub-Broker Code': [''],
            'Brokerage Percentage': [''],
            'Commission': [''],
            'Investor ID': [''],
            'Report Date': [''],
            'Report Time': [''],
            'Transaction Sub': [''],
            'Application Number': [''],
            'Transaction ID': [''],
            'Transaction Description': ['Purchase'],
            'Transaction Type': ['Purchase'],
            'Instrument Date': [''],
            'Instrument Bank': [''],
            'Dividend Option': [''],
            'Purchase Amount': ['5000.00'],
            'Purchase Date': ['01-Jan-2024'],
            'Switch Fund Date': [''],
            'Transaction Flag': ['P'],
            'Nav': ['100.00'],
            'Purchase Transaction No': [''],
            'STT': ['0'],
            'Load Percentage': ['0'],
            'Load Amount': ['0'],
            'Purchase Units': ['50.0'],
            'Ihno': [''],
            'Branch Code': [''],
            'Inward Number': [''],
            'PAN1': ['ABCDE1234F'],
            'Remarks': ['Test Txn'],
            'Nav Date': ['01-Jan-2024'],
            'PAN2': [''],
            'PAN3': [''],
            'TDSAmount': ['0'],
            'Scheme': [''],
            'Plan': [''],
            'ToProductCode': [''],
            'td_trxnmode': [''],
            'ClientId': [''],
            'DpId': [''],
            'Status': [''],
            'RejTrnoOrgNo': [''],
            'SubTranType': ['P'],
            'TrCharges': [''],
            'ATMCardStatus': [''],
            'ATMCardRemarks': [''],
            'NCT Change Date': [''],
            'ISIN': [''],
            'CityCategory': [''],
            'PortDate': [''],
            'NewUnqno': [''],
            'EUIN': [''],
            'Sub Broker ARN Code': [''],
            'EUIN Valid Indicator': [''],
            'EUIN Declaration Indicator': [''],
            'AssetType': [''],
            'SIP Regn Date': [''],
            'DivPer': [''],
            'GuardPanNo': [''],
            'Common Account Number': [''],
            'Exchange OrgTrType': [''],
            'Electronic transaction Flag': [''],
            'sipregslno': [''],
            'chequeclearnce': [''],
            'InvestorState': [''],
            'Retail Flag': [''],
            'Stamp Duty Charges': ['0.005'],
            'Feed Type': ['']
        }
        df = pd.DataFrame(data)
        
        # Save to CSV in memory
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue().encode('utf-8')

        uploaded_file = SimpleUploadedFile("karvy_feed.csv", csv_content)
        rta_file = RTAFile.objects.create(rta_type=RTAFile.RTA_KARVY, file_name="karvy_feed.csv", file=uploaded_file)

        parser = KarvyCSVParser(rta_file)
        parser.parse()

        self.assertEqual(rta_file.status, RTAFile.STATUS_PROCESSED)
        txn = Transaction.objects.filter(txn_number__startswith="KTXN01").first() # Using startswith as fingerprint is appended
        self.assertIsNotNone(txn)
        self.assertEqual(txn.units, Decimal("50.0"))
        self.assertEqual(txn.scheme, self.scheme)
        self.assertEqual(txn.description, "Purchase")
        self.assertEqual(txn.stamp_duty, Decimal("0.005"))
