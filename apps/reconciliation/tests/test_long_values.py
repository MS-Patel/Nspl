from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.reconciliation.models import RTAFile, Transaction
from apps.reconciliation.parsers import CAMSXLSParser, KarvyXLSParser
from apps.users.models import InvestorProfile, User
from apps.products.models import Scheme, AMC, SchemeCategory
import pandas as pd
import io

class CAMSLongValueTest(TestCase):
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

    def test_cams_parser_long_values(self):
        # Create a DataFrame with a long transaction type and flag
        long_type = "T" * 50  # 50 chars, previously max 20
        long_flag = "F" * 50  # 50 chars, previously max 20

        data = {
            'pan': ['ABCDE1234F'],
            'inv_name': ['John Doe'],
            'prodcode': ['HDFC100'],
            'folio_no': ['12345/67'],
            'trxnno': ['TXN_LONG_001'],
            'traddate': ['2024-01-01'],
            'units': [10.5],
            'amount': [1000.0],
            'trxntype': [long_type],
            'trxnstat': ['OK'],
            'postdate': ['2024-01-02'],
            'trxn_nature': ['Purchase'],
            'trxn_type_flag': [long_flag]
        }
        df = pd.DataFrame(data)

        # Save to BytesIO
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)

        uploaded_file = SimpleUploadedFile("cams_long.xlsx", output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        rta_file = RTAFile.objects.create(rta_type=RTAFile.RTA_CAMS, file_name="cams_long.xlsx", file=uploaded_file)

        parser = CAMSXLSParser(rta_file)
        parser.parse()

        # Check status
        self.assertEqual(rta_file.status, RTAFile.STATUS_PROCESSED)

        # Verify transaction
        txn = Transaction.objects.filter(txn_number__startswith="TXN_LONG_001").first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.txn_type_code, long_type)
        self.assertEqual(txn.tr_flag, long_flag)

    def test_karvy_parser_long_values(self):
        long_type = "K" * 50
        long_flag = "F" * 50

        data = {
            'pan1': ['ABCDE1234F'],
            'invname': ['John Doe'],
            'fmcode': ['HDFC100'],
            'td_acno': ['12345/67'],
            'td_trno': ['KTXN_LONG_001'],
            'navdate': ['2024-01-01'],
            'td_prdt': ['2024-01-01'],
            'td_units': [10.5],
            'td_amt': [1000.0],
            'td_trtype': [long_type],
            'trnstat': ['OK'],
            'trdesc': ['Purchase'],
            'trflag': [long_flag],
            'trxn_type_flag': ['']
        }
        df = pd.DataFrame(data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Karvy uses header at index 1 usually
            df.to_excel(writer, index=False, startrow=1)
        output.seek(0)

        uploaded_file = SimpleUploadedFile("karvy_long.xlsx", output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        rta_file = RTAFile.objects.create(rta_type=RTAFile.RTA_KARVY, file_name="karvy_long.xlsx", file=uploaded_file)

        parser = KarvyXLSParser(rta_file)
        parser.parse()

        self.assertEqual(rta_file.status, RTAFile.STATUS_PROCESSED)
        txn = Transaction.objects.filter(txn_number__startswith="KTXN_LONG_001").first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.txn_type_code, long_type)
        self.assertEqual(txn.tr_flag, long_flag)
