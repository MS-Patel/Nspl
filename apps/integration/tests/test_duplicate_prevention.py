from django.test import TestCase
from unittest.mock import patch, MagicMock
from decimal import Decimal
import datetime
from django.utils import timezone
from apps.users.models import User, InvestorProfile
from apps.products.models import Scheme, AMC, SchemeCategory
from apps.reconciliation.models import Transaction, Holding
from apps.integration.sync_utils import sync_bse_daily_reports

class SyncDuplicatePreventionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.investor = InvestorProfile.objects.create(
            user=self.user,
            pan='ABCDE1234F',
            ucc_code='TESTUCC'
        )
        self.amc = AMC.objects.create(name='Test AMC', code='TAMC')
        self.category = SchemeCategory.objects.create(name='Equity', code='EQ')
        self.scheme = Scheme.objects.create(
            amc=self.amc,
            category=self.category,
            name='Test Scheme',
            scheme_code='SCHEME1',
            isin='INF123456789'
        )

    @patch('apps.integration.sync_utils.recalculate_holding')
    @patch('apps.integration.sync_utils.BSEStarMFClient')
    def test_prevent_duplicate_confirmed_transaction(self, MockBSEClient, mock_recalc):
        """
        Test that if a Confirmed (is_provisional=False) transaction exists,
        BSE Sync does NOT overwrite it or create a duplicate.
        """
        # Create existing confirmed transaction
        Transaction.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            folio_number='FOLIO99',
            txn_number='RTA12345', # Different from BSE ID usually
            bse_order_id='ORD100',
            amount=1000,
            units=10,
            date=datetime.date(2023, 10, 27),
            is_provisional=False, # Confirmed by RTA
            source=Transaction.SOURCE_RTA
        )

        # Mock BSE Response with same Order ID
        mock_instance = MockBSEClient.return_value
        mock_resp = MagicMock()
        mock_resp.Status = '100'

        detail = MagicMock()
        detail.OrderNo = 'ORD100'
        detail.ClientCode = 'TESTUCC'
        detail.SchemeCode = 'SCHEME1'
        detail.FolioNo = 'FOLIO99'
        detail.AllottedUnit = '10.000' # Matches
        detail.AllottedAmt = '1000.00'
        detail.Nav = '100.00'
        detail.AllotmentDate = '27/10/2023'

        mock_resp.AllotmentDetails.AllotmentDetails = [detail]
        mock_instance.get_allotment_statement.return_value = mock_resp

        # Mock Redemption empty
        mock_redemp = MagicMock()
        mock_redemp.Status = '100'
        mock_redemp.RedemptionDetails = None
        mock_instance.get_redemption_statement.return_value = mock_redemp

        # Run Sync
        sync_bse_daily_reports(days=1)

        # Assertions
        # 1. Should still be 1 transaction
        self.assertEqual(Transaction.objects.filter(bse_order_id='ORD100').count(), 1)

        # 2. Should still be SOURCE_RTA and not provisional
        txn = Transaction.objects.get(bse_order_id='ORD100')
        self.assertEqual(txn.source, Transaction.SOURCE_RTA)
        self.assertFalse(txn.is_provisional)
        self.assertEqual(txn.txn_number, 'RTA12345') # Should not be overwritten by ORD100

        # 3. Recalculate holding should NOT be called because we skipped it
        mock_recalc.assert_not_called()

    @patch('apps.integration.sync_utils.recalculate_holding')
    @patch('apps.integration.sync_utils.BSEStarMFClient')
    def test_update_existing_provisional_transaction(self, MockBSEClient, mock_recalc):
        """
        Test that if a Provisional transaction exists, BSE Sync updates it.
        """
        # Create existing provisional transaction
        Transaction.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            folio_number='FOLIO99',
            txn_number='ORD200',
            bse_order_id='ORD200',
            amount=1000,
            units=0, # Initially 0, waiting for allotment
            date=datetime.date(2023, 10, 27),
            is_provisional=True,
            source=Transaction.SOURCE_BSE
        )

        # Mock BSE Response
        mock_instance = MockBSEClient.return_value
        mock_resp = MagicMock()
        mock_resp.Status = '100'

        detail = MagicMock()
        detail.OrderNo = 'ORD200'
        detail.ClientCode = 'TESTUCC'
        detail.SchemeCode = 'SCHEME1'
        detail.FolioNo = 'FOLIO99'
        detail.AllottedUnit = '15.000' # Updated units
        detail.AllottedAmt = '1500.00'
        detail.Nav = '100.00'
        detail.AllotmentDate = '27/10/2023'

        mock_resp.AllotmentDetails.AllotmentDetails = [detail]
        mock_instance.get_allotment_statement.return_value = mock_resp

        # Mock Redemption empty
        mock_redemp = MagicMock()
        mock_redemp.Status = '100'
        mock_redemp.RedemptionDetails = None
        mock_instance.get_redemption_statement.return_value = mock_redemp

        # Run Sync
        sync_bse_daily_reports(days=1)

        # Assertions
        self.assertEqual(Transaction.objects.filter(bse_order_id='ORD200').count(), 1)
        txn = Transaction.objects.get(bse_order_id='ORD200')
        self.assertEqual(txn.units, Decimal('15.000'))
        self.assertEqual(txn.amount, Decimal('1500.00'))
        self.assertTrue(txn.is_provisional)

        # Recalculate should be called
        mock_recalc.assert_called_with(self.investor, self.scheme, 'FOLIO99')

    @patch('apps.integration.sync_utils.recalculate_holding')
    @patch('apps.integration.sync_utils.BSEStarMFClient')
    def test_create_new_provisional_transaction(self, MockBSEClient, mock_recalc):
        """
        Test that if no transaction exists, BSE Sync creates a new provisional one.
        """
        # Mock BSE Response
        mock_instance = MockBSEClient.return_value
        mock_resp = MagicMock()
        mock_resp.Status = '100'

        detail = MagicMock()
        detail.OrderNo = 'ORD300'
        detail.ClientCode = 'TESTUCC'
        detail.SchemeCode = 'SCHEME1'
        detail.FolioNo = 'FOLIO88'
        detail.AllottedUnit = '20.000'
        detail.AllottedAmt = '2000.00'
        detail.Nav = '100.00'
        detail.AllotmentDate = '27/10/2023'

        mock_resp.AllotmentDetails.AllotmentDetails = [detail]
        mock_instance.get_allotment_statement.return_value = mock_resp

        # Mock Redemption empty
        mock_redemp = MagicMock()
        mock_redemp.Status = '100'
        mock_redemp.RedemptionDetails = None
        mock_instance.get_redemption_statement.return_value = mock_redemp

        # Run Sync
        sync_bse_daily_reports(days=1)

        # Assertions
        self.assertEqual(Transaction.objects.filter(bse_order_id='ORD300').count(), 1)
        txn = Transaction.objects.get(bse_order_id='ORD300')
        self.assertEqual(txn.units, Decimal('20.000'))
        self.assertTrue(txn.is_provisional)

        # Recalculate should be called
        mock_recalc.assert_called_with(self.investor, self.scheme, 'FOLIO88')
