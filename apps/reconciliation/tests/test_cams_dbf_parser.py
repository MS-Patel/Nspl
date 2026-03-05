from django.test import TestCase
from decimal import Decimal
import pandas as pd
from datetime import date
from unittest.mock import MagicMock, patch
from apps.reconciliation.parsers import DBFParser
from apps.reconciliation.models import Transaction, RTAFile
from apps.users.models import InvestorProfile, User
from apps.products.models import Scheme, AMC

class TestCAMSDBFParser(TestCase):
    def setUp(self):
        # Setup basic data
        self.user = User.objects.create_user(username='TESTPAN123', password='password')
        self.investor = InvestorProfile.objects.create(user=self.user, pan='TESTPAN123', firstname='John', lastname='Doe')
        
        self.amc = AMC.objects.create(name='Test AMC', code='101')
        self.scheme = Scheme.objects.create(amc=self.amc, name='Test Scheme', scheme_code='PROD001', channel_partner_code='PROD001', isin='INF123456789')
        
        self.rta_file = RTAFile.objects.create(rta_type=RTAFile.RTA_CAMS, file_name='test.dbf')
        self.parser = DBFParser(rta_file_obj=self.rta_file, file_path='dummy_path.dbf')

    @patch('simpledbf.Dbf5')
    def test_parse_cams_dbf(self, mock_dbf_cls):
        # Mock DBF Data matching the user provided columns
        data = {
            'amc_code': ['101'],
            'folio_no': ['FOLIO123'],
            'prodcode': ['PROD001'],
            'scheme': ['Test Scheme'],
            'inv_name': ['John Doe'],
            'trxntype': ['P'], # Purchase
            'trxnno': ['TXN001'],
            'trxnmode': ['N'],
            'trxnstat': ['OK'],
            'usercode': ['USER1'],
            'usrtrxno': ['UTXN1'],
            'traddate': ['01-Jan-2023'],
            'postdate': ['02-Jan-2023'],
            'purprice': ['10.50'],
            'units': ['100.00'],
            'amount': ['1050.00'],
            'brokcode': ['ARN-001'],
            'subbrok': ['SUB-001'],
            'brokperc': ['0.1'],
            'brokcomm': ['1.05'],
            'altfolio': ['ALT123'],
            'rep_date': ['03-Jan-2023'],
            'time1': ['10:00'],
            'trxnsubtyp': ['N'],
            'applicatio': ['APP001'],
            'trxn_natur': ['Purchase Transaction'], # txn_natur
            'tax': ['0.00'],
            'total_tax': ['0.00'],
            'te_15h': ['N'],
            'micr_no': ['MICR001'],
            'remarks': ['Test Remark'],
            'swflag': ['NA'],
            'old_folio': ['OLD123'],
            'seq_no': ['1'],
            'reinvest_f': ['N'],
            'mult_brok': ['N'],
            'stt': ['0.00'],
            'location': ['Mumbai'],
            'scheme_typ': ['Equity'],
            'tax_status': ['Resident'],
            'load': ['0.00'],
            'scanrefno': ['SCAN001'],
            'pan': ['TESTPAN123'],
            'inv_iin': ['MIN001'], # Mapped to min_no
            'targ_src_s': ['TargetScheme'],
            'trxn_type_': ['P'], # tr_flag
            'ticob_trty': [''],
            'ticob_trno': [''],
            'ticob_post': [''],
            'dp_id': ['DP001'],
            'trxn_charg': ['0.00'],
            'eligib_amt': ['1050.00'],
            'src_of_txn': ['Online'],
            'trxn_suffi': ['Suffix'],
            'siptrxnno': ['SIP001'],
            'ter_locati': ['TerLoc'],
            'euin': ['EUIN001'],
            'euin_valid': ['Y'],
            'euin_opted': ['Y'],
            'sub_brk_ar': ['ARN-SUB'],
            'exch_dc_fl': ['D'],
            'src_brk_co': ['SRC001'],
            'sys_regn_d': ['01-Jan-2023'],
            'ac_no': ['AC001'],
            'bank_name': ['HDFC'],
            'reversal_c': [''],
            'exchange_f': ['BSE'],
            'ca_initiat': [''],
            'gst_state_': ['MH'],
            'igst_amoun': ['0'],
            'cgst_amoun': ['0'],
            'sgst_amoun': ['0'],
            'rev_remark': [''],
            'original_t': [''],
            'stamp_duty': ['0.005'],
            'folio_old': [''],
            'scheme_fol': [''],
            'amc_ref_no': ['AMC001'],
            'request_re': [''],
            'transmissi': ['']
        }
        
        df = pd.DataFrame(data)
        
        mock_dbf_instance = MagicMock()
        mock_dbf_instance.to_dataframe.return_value = df
        mock_dbf_cls.return_value = mock_dbf_instance

        # Run Parse
        self.parser.parse()

        # Check Transaction Created
        # The new logic uses only the fingerprint as the txn_number.
        # Since there is only one transaction created in this test, we can just get it.
        txn = Transaction.objects.first()
        self.assertIsNotNone(txn, "Transaction was not created")
        self.assertEqual(txn.investor, self.investor)
        self.assertEqual(txn.scheme, self.scheme)
        self.assertEqual(txn.folio_number, 'FOLIO123')
        self.assertEqual(txn.amount, Decimal('1050.00'))
        self.assertEqual(txn.units, Decimal('100.00'))
        self.assertEqual(txn.txn_type_code, 'P')
        self.assertEqual(txn.rta_code, 'CAMS')
        
        # Check New Fields
        self.assertEqual(txn.amc_code, '101')
        # self.assertEqual(txn.product_code, 'PROD001') # Mapped from prodcode, check implementation
        self.assertEqual(txn.txn_nature, 'Purchase Transaction')
        self.assertEqual(txn.tax_status, 'Resident')
        self.assertEqual(txn.micr_no, 'MICR001')
        self.assertEqual(txn.old_folio, 'OLD123')
        self.assertEqual(txn.reinvest_flag, 'N')
        self.assertEqual(txn.mult_brok, 'N')
        self.assertEqual(txn.scan_ref_no, 'SCAN001')
        self.assertEqual(txn.min_no, 'MIN001')
        self.assertEqual(txn.dp_id, 'DP001')
        self.assertEqual(txn.siptrxnno, 'SIP001')
        self.assertEqual(txn.euin, 'EUIN001')
        self.assertEqual(txn.bank_name, 'HDFC')
        self.assertEqual(txn.ac_no, 'AC001')
        self.assertEqual(txn.stamp_duty, Decimal('0.005'))

    def test_holding_recalculation_cams_logic(self):
        # Create a transaction manually to test holding logic
        # 1. Purchase (P) -> Add
        Transaction.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            folio_number='FOLIO_TEST',
            rta_code='CAMS',
            txn_type_code='P',
            txn_number='TXN_P',
            date=date(2023, 1, 1),
            amount=Decimal('1000'),
            units=Decimal('100'), # NAV 10
            nav=Decimal('10')
        )
        
        from apps.reconciliation.utils.reconcile import recalculate_holding
        recalculate_holding(self.investor, self.scheme, 'FOLIO_TEST')
        
        holding = self.investor.holdings.get(scheme=self.scheme, folio_number='FOLIO_TEST')
        self.assertEqual(holding.units, Decimal('100'))
        self.assertEqual(holding.average_cost, Decimal('10')) # 1000/100

        # 2. Redemption (R) -> Sub
        Transaction.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            folio_number='FOLIO_TEST',
            rta_code='CAMS',
            txn_type_code='R',
            txn_number='TXN_R',
            date=date(2023, 1, 2),
            amount=Decimal('550'), # NAV 11
            units=Decimal('50'),
            nav=Decimal('11')
        )
        
        recalculate_holding(self.investor, self.scheme, 'FOLIO_TEST')
        holding.refresh_from_db()
        self.assertEqual(holding.units, Decimal('50')) # 100 - 50
        self.assertEqual(holding.average_cost, Decimal('10')) # Cost basis unchanged on redemption

        # 3. Dividend Reinvest (DR) -> Add
        Transaction.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            folio_number='FOLIO_TEST',
            rta_code='CAMS',
            txn_type_code='DR',
            txn_number='TXN_DR',
            date=date(2023, 1, 3),
            amount=Decimal('100'),
            units=Decimal('10'), # NAV 10
            nav=Decimal('10')
        )
        
        recalculate_holding(self.investor, self.scheme, 'FOLIO_TEST')
        holding.refresh_from_db()
        self.assertEqual(holding.units, Decimal('60')) # 50 + 10
        # WAC: (50 * 10 + 100) / 60 = 600 / 60 = 10. DR increases cost basis? 
        # Usually DR is treated as new purchase. Cost = Amount Reinvested.
        # Yes, logic implements it as purchase.
        
        # 4. Rejection (J) -> Reversal (SUB)
        # Using Legacy Logic: 'J' is in GENERIC_REVERSAL_CODES
        # Positive units + no specific description -> Defaults to Purchase Reversal (SUB)
        Transaction.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            folio_number='FOLIO_TEST',
            rta_code='CAMS',
            txn_type_code='J',
            txn_number='TXN_J',
            date=date(2023, 1, 4),
            amount=Decimal('100'), # Same as DR
            units=Decimal('10'),
            nav=Decimal('10')
        )
        
        recalculate_holding(self.investor, self.scheme, 'FOLIO_TEST')
        holding.refresh_from_db()
        # Expect 50 (60 - 10)
        self.assertEqual(holding.units, Decimal('50')) 
