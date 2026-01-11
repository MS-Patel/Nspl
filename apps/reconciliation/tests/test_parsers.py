import os
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.reconciliation.models import RTAFile, Transaction, Holding
from apps.reconciliation.parsers import CAMSParser, KarvyParser, FranklinParser
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

class CAMSParserTest(ParserTestBase):
    def test_cams_parser(self):
        # Format: DTL|...|SCHEME|...|TYPE|TXN_NO|...|UNITS|AMOUNT|...|DATE|...|PAN
        # Indices: 1:Folio, 3:Scheme, 8:Type, 9:TxnNo, 12:Units, 13:Amt, 15:Date, 18:PAN
        row_data = ["DTL", "12345/67", "dummy", "HDFC100", "ISIN", "John Doe", "x", "x", "P", "TXN001", "x", "x", "10.5", "1000.00", "x", "01-Jan-2024", "x", "x", "ABCDE1234F"]
        while len(row_data) < 20: row_data.append("")

        file_content = "HED|HEADER\n" + "|".join(row_data)
        uploaded_file = SimpleUploadedFile("cams_feed.txt", file_content.encode('utf-8'))
        rta_file = RTAFile.objects.create(rta_type=RTAFile.RTA_CAMS, file_name="cams.txt", file=uploaded_file)

        parser = CAMSParser(rta_file)
        parser.parse()

        self.assertEqual(rta_file.status, RTAFile.STATUS_PROCESSED)
        txn = Transaction.objects.first()
        self.assertEqual(txn.txn_number, "TXN001")
        self.assertEqual(txn.units, Decimal("10.5"))

class KarvyParserTest(ParserTestBase):
    def test_karvy_parser(self):
        # Assuming Karvy/MFD Layout (Pipe):
        # 0: AMC, 1: Scheme, 3: Folio, 5: Type, 6: TxnNo, 7: Units, 8: Amount, 9: Date, 14: PAN
        row_data = ["AMC", "HDFC100", "Name", "12345/K", "InvName", "P", "KTXN01", "50.0", "5000.00", "01/01/2024", "x", "x", "x", "x", "ABCDE1234F"]

        file_content = "Header\n" + "|".join(row_data)
        uploaded_file = SimpleUploadedFile("karvy_feed.txt", file_content.encode('utf-8'))
        rta_file = RTAFile.objects.create(rta_type=RTAFile.RTA_KARVY, file_name="karvy.txt", file=uploaded_file)

        parser = KarvyParser(rta_file)
        parser.parse()

        self.assertEqual(rta_file.status, RTAFile.STATUS_PROCESSED)
        txn = Transaction.objects.get(txn_number="KTXN01")
        self.assertEqual(txn.units, Decimal("50.0"))
        self.assertEqual(txn.scheme, self.scheme)

class FranklinParserTest(ParserTestBase):
    def test_franklin_parser(self):
        # Assuming FT Layout (Pipe):
        # 1: Scheme, 3: Folio, 5: Type, 6: TxnNo, 7: Units, 8: Amt, 9: Date, 18: PAN
        row_data = ["COMP", "HDFC100", "Name", "12345/F", "InvName", "P", "FTXN01", "25.0", "2500.00", "01-01-2024", "x", "x", "x", "x", "x", "x", "x", "x", "ABCDE1234F"]

        file_content = "Header\n" + "|".join(row_data)
        uploaded_file = SimpleUploadedFile("franklin_feed.txt", file_content.encode('utf-8'))
        rta_file = RTAFile.objects.create(rta_type=RTAFile.RTA_FRANKLIN, file_name="ft.txt", file=uploaded_file)

        parser = FranklinParser(rta_file)
        parser.parse()

        self.assertEqual(rta_file.status, RTAFile.STATUS_PROCESSED)
        txn = Transaction.objects.get(txn_number="FTXN01")
        self.assertEqual(txn.units, Decimal("25.0"))
        self.assertEqual(txn.scheme, self.scheme)
