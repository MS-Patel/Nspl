import os
import pandas as pd
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.reconciliation.models import RTAFile, Transaction
from apps.reconciliation.parsers import CAMSXLSParser, KarvyXLSParser
from apps.users.models import InvestorProfile, User
from apps.products.models import Scheme, AMC, SchemeCategory
from decimal import Decimal
from datetime import date

class ReproductionTestCase(TestCase):
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

    def test_cams_xls_parser_case_sensitivity_fixed(self):
        """
        Tests if CAMSXLSParser NOW works with uppercase columns (e.g., 'PAN' vs 'pan').
        And checks if a transaction is created WITH an investor.
        And checks if is_offline is True.
        """
        # Create a DataFrame with uppercase columns
        data = {
            'PAN': ['ABCDE1234F'],  # Uppercase
            'INV_NAME': ['John Doe'],
            'PRODCODE': ['HDFC100'],
            'FOLIO_NO': ['12345/67'],
            'TRXNNO': ['TXN001'],
            'TRADDATE': ['2024-01-01'],
            'UNITS': [10.5],
            'AMOUNT': [1000.0],
            'TRXNTYPE': ['P']
        }
        df = pd.DataFrame(data)

        # Save to a temporary Excel file
        file_path = 'temp_cams.xlsx'
        df.to_excel(file_path, index=False)

        with open(file_path, 'rb') as f:
            uploaded_file = SimpleUploadedFile("cams.xlsx", f.read())

        rta_file = RTAFile.objects.create(rta_type=RTAFile.RTA_CAMS, file_name="cams.xlsx", file=uploaded_file)

        # Run Parser
        parser = CAMSXLSParser(rta_file)
        parser.parse()

        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)

        # Assertions
        # 1. Check if Transaction exists
        txn = Transaction.objects.filter(txn_number='TXN001').first()
        self.assertIsNotNone(txn, "Transaction TXN001 should be created now.")

        # 2. Check Investor
        self.assertIsNotNone(txn.investor, "Transaction should have an Investor linked.")
        self.assertEqual(txn.investor.pan, "ABCDE1234F")

        # 3. Check is_offline flag
        self.assertTrue(txn.investor.is_offline, "Investor should be marked as offline.")

    def test_duplicate_upload_behavior(self):
        """
        Tests if re-uploading the same file duplicates holdings.
        """
        # Create a DataFrame with proper columns (lowercase as expected by current parser to ensure it runs)
        data = {
            'pan': ['ABCDE1234F'],
            'inv_name': ['John Doe'],
            'prodcode': ['HDFC100'],
            'folio_no': ['12345/67'],
            'trxnno': ['TXN002'],
            'traddate': ['2024-01-01'],
            'units': [100],
            'amount': [10000.0],
            'trxntype': ['P']
        }
        df = pd.DataFrame(data)
        file_path = 'temp_cams_dup.xlsx'
        df.to_excel(file_path, index=False)

        with open(file_path, 'rb') as f:
            content = f.read()

        # Upload 1
        uploaded_file1 = SimpleUploadedFile("cams1.xlsx", content)
        rta_file1 = RTAFile.objects.create(rta_type=RTAFile.RTA_CAMS, file_name="cams1.xlsx", file=uploaded_file1)
        parser1 = CAMSXLSParser(rta_file1)
        parser1.parse()

        # Check Holdings
        investor = InvestorProfile.objects.filter(pan='ABCDE1234F').first()
        holding = investor.holdings.filter(scheme=self.scheme, folio_number='12345/67').first()
        self.assertEqual(holding.units, Decimal('100'))

        # Upload 2 (Same file)
        uploaded_file2 = SimpleUploadedFile("cams2.xlsx", content)
        rta_file2 = RTAFile.objects.create(rta_type=RTAFile.RTA_CAMS, file_name="cams2.xlsx", file=uploaded_file2)
        parser2 = CAMSXLSParser(rta_file2)
        parser2.parse()

        # Check Holdings Again
        holding.refresh_from_db()
        self.assertEqual(holding.units, Decimal('100'), "Holding units doubled after re-upload!")

        if os.path.exists(file_path):
            os.remove(file_path)
