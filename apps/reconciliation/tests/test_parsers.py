import os
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.reconciliation.models import RTAFile, Transaction, Holding
from apps.reconciliation.parsers import CAMSParser
from apps.users.models import InvestorProfile, User
from apps.products.models import Scheme, AMC, SchemeCategory
from datetime import date
from decimal import Decimal

class CAMSParserTest(TestCase):
    def setUp(self):
        # Setup Master Data
        self.amc = AMC.objects.create(name="HDFC Mutual Fund", code="HDFC")
        self.category = SchemeCategory.objects.create(name="Equity")
        self.scheme = Scheme.objects.create(
            name="HDFC Top 100",
            scheme_code="HDFC100", # Matches row[3]
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

    def test_cams_parser(self):
        # Create a sample CAMS pipe-separated content
        # Format: HED...
        # DTL|AMC|FOLIO|SCHEME|ISIN|INV_NAME|...|TYPE|TXN_NO|...|UNITS|AMOUNT|...|DATE|...|PAN
        # Indices:
        # 1: Folio (12345)
        # 3: Scheme (HDFC100)
        # 8: Type (P)
        # 9: TxnNo (TXN001)
        # 12: Units (10.5)
        # 13: Amount (1000.00)
        # 15: Date (01-Jan-2024)
        # 18: PAN (ABCDE1234F)

        # Minimal fake row with enough separators
        row_data = ["DTL", "12345/67", "dummy", "HDFC100", "ISIN", "John Doe", "x", "x", "P", "TXN001", "x", "x", "10.5", "1000.00", "x", "01-Jan-2024", "x", "x", "ABCDE1234F"]
        # Ensure length is > 18
        while len(row_data) < 20:
            row_data.append("")

        file_content = "HED|HEADER\n" + "|".join(row_data)

        uploaded_file = SimpleUploadedFile("cams_feed.txt", file_content.encode('utf-8'))

        rta_file = RTAFile.objects.create(
            rta_type=RTAFile.RTA_CAMS,
            file_name="cams_feed.txt",
            file=uploaded_file
        )

        parser = CAMSParser(rta_file)
        parser.parse()

        # Check RTAFile status
        rta_file.refresh_from_db()
        self.assertEqual(rta_file.status, RTAFile.STATUS_PROCESSED)

        # Check Transaction
        txn = Transaction.objects.first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.txn_number, "TXN001")
        self.assertEqual(txn.amount, Decimal("1000.00"))
        self.assertEqual(txn.units, Decimal("10.5"))
        self.assertEqual(txn.scheme, self.scheme)
        self.assertEqual(txn.investor, self.investor)

        # Check Holding
        holding = Holding.objects.get(folio_number="12345/67")
        self.assertEqual(holding.units, Decimal("10.5"))

    def test_cams_parser_redemption(self):
        # Test Subtraction
        # Purchase 100
        row1 = ["DTL", "12345/67", "dummy", "HDFC100", "ISIN", "John Doe", "x", "x", "P", "TXN001", "x", "x", "100", "10000", "x", "01-Jan-2024", "x", "x", "ABCDE1234F"]
        # Redeem 20
        row2 = ["DTL", "12345/67", "dummy", "HDFC100", "ISIN", "John Doe", "x", "x", "R", "TXN002", "x", "x", "20", "2000", "x", "02-Jan-2024", "x", "x", "ABCDE1234F"]

        # Fill blanks
        while len(row1) < 20: row1.append("")
        while len(row2) < 20: row2.append("")

        file_content = "HED|HEADER\n" + "|".join(row1) + "\n" + "|".join(row2)

        uploaded_file = SimpleUploadedFile("cams_feed.txt", file_content.encode('utf-8'))
        rta_file = RTAFile.objects.create(rta_type=RTAFile.RTA_CAMS, file_name="cams_feed_red.txt", file=uploaded_file)

        parser = CAMSParser(rta_file)
        parser.parse()

        holding = Holding.objects.get(folio_number="12345/67")
        # 100 - 20 = 80
        self.assertEqual(holding.units, Decimal("80"))
