from django.test import TestCase
from django.utils import timezone
from apps.payouts.models import BrokerageImport, BrokerageTransaction
from apps.products.models import Scheme, AMC, SchemeCategory
from apps.payouts.utils import process_cams_file, process_karvy_file
import pandas as pd
import os
from unittest.mock import MagicMock, patch

class TestBrokerageParsing(TestCase):
    def setUp(self):
        # Create AMC and Scheme
        self.amc = AMC.objects.create(name="HDFC Mutual Fund", code="HDFC")
        self.category = SchemeCategory.objects.create(name="Equity", code="EQ")

        self.scheme1 = Scheme.objects.create(
            amc=self.amc,
            name="HDFC Top 100 Fund",
            scheme_code="HDFC100", # BSE Code
            rta_scheme_code="H100",  # RTA Code
            category=self.category,
            isin="INF179K01BE2",
            unique_no=12345
        )

        self.import_obj = BrokerageImport.objects.create(month=1, year=2024)

    @patch('apps.payouts.utils.pd.read_csv')
    def test_cams_parsing_scheme_lookup(self, mock_read_csv):
        # Mock CSV Data for CAMS
        # Use simple dictionary for DataFrame constructor
        data = {
            'BROK_CODE': ['ARN-123'],
            'BRKAGE_AMT': [100.0],
            'PLOT_AMOUN': [10000.0],
            'INV_NAME': ['John Doe'],
            'FOLIO_NO': ['123/456'],
            'SCHEME_COD': ['H100'], # Should match rta_scheme_code
            'TRXN_DATE': ['01-Jan-2024'],
            'SCHEME_NAM': ['HDFC Top 100']
        }
        df = pd.DataFrame(data)
        mock_read_csv.return_value = df

        # Mock file path (cams_file.path)
        self.import_obj.cams_file = MagicMock()
        self.import_obj.cams_file.path = "dummy.csv"

        process_cams_file(self.import_obj)

        txn = BrokerageTransaction.objects.first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.scheme, self.scheme1)
        self.assertEqual(txn.scheme_name, 'HDFC Top 100')

    @patch('apps.payouts.utils.pd.read_csv')
    def test_karvy_parsing_scheme_lookup_fallback(self, mock_read_csv):
        # Mock CSV Data for Karvy
        data = {
            'Broker Code': ['ARN-123'],
            'Brokerage (in Rs.)': [50.0],
            'Amount (in Rs.)': [5000.0],
            'Investor Name': ['Jane Doe'],
            'Account Number': ['987654321'],
            'Product Code': ['HDFC100'], # Should match scheme_code (BSE) as fallback
            'Transaction Date': ['01/01/2024'],
            'Fund Description': ['HDFC Top 100']
        }
        df = pd.DataFrame(data)
        mock_read_csv.return_value = df

        # Karvy file path
        self.import_obj.karvy_file = MagicMock()
        self.import_obj.karvy_file.path = "dummy_karvy.csv"

        process_karvy_file(self.import_obj)

        txn = BrokerageTransaction.objects.first()
        self.assertIsNotNone(txn)
        # Note: In setUp, scheme_code='HDFC100'. logic checks rta, amc, then scheme_code.
        self.assertEqual(txn.scheme, self.scheme1)
