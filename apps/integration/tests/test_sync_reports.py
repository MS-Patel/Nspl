from django.test import TestCase
from unittest.mock import patch, MagicMock
from decimal import Decimal
import datetime
from django.utils import timezone

from apps.users.models import User, InvestorProfile
from apps.products.models import Scheme, AMC, SchemeCategory
from apps.investments.models import Order
from apps.reconciliation.models import Transaction
from apps.integration.sync_utils import sync_bse_daily_reports

class SyncBSEReportsTest(TestCase):
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

    @patch('apps.integration.sync_utils.BSEStarMFClient')
    def test_sync_order_status(self, MockBSEClient):
        # Setup Order
        order = Order.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            amount=1000,
            status=Order.SENT_TO_BSE,
            bse_order_id='ORD123',
            unique_ref_no='REF123'
        )

        # Mock Response
        mock_instance = MockBSEClient.return_value
        mock_resp = MagicMock()
        mock_resp.Status = '100'

        detail = MagicMock()
        detail.OrderNumber = 'ORD123'
        detail.OrderStatus = 'APPROVED'
        detail.OrderRemarks = 'Approved by BSE'

        mock_resp.OrderDetails.OrderDetails = [detail]
        mock_instance.get_order_status.return_value = mock_resp

        # Run Sync
        sync_bse_daily_reports(days=1)

        # Verify
        order.refresh_from_db()
        self.assertEqual(order.status, Order.APPROVED)
        self.assertEqual(order.bse_remarks, 'Approved by BSE')

    @patch('apps.integration.sync_utils.BSEStarMFClient')
    def test_sync_allotment(self, MockBSEClient):
        # Mock Response
        mock_instance = MockBSEClient.return_value
        mock_resp = MagicMock()
        mock_resp.Status = '100'

        detail = MagicMock()
        detail.OrderNo = 'ORD456'
        detail.ClientCode = 'TESTUCC'
        detail.SchemeCode = 'SCHEME1'
        detail.FolioNo = 'FOLIO99'
        detail.AllottedUnit = '10.0'
        detail.AllottedAmt = '1000.0'
        detail.Nav = '100.0'
        detail.AllotmentDate = '27/10/2023'

        mock_resp.AllotmentDetails.AllotmentDetails = [detail]
        mock_instance.get_allotment_statement.return_value = mock_resp

        # Run Sync
        sync_bse_daily_reports(days=1)

        # Verify Transaction Created
        txn = Transaction.objects.filter(bse_order_id='ORD456').first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.investor, self.investor)
        self.assertEqual(txn.scheme, self.scheme)
        self.assertEqual(txn.folio_number, 'FOLIO99')
        self.assertEqual(txn.units, Decimal('10.0'))
        self.assertEqual(txn.amount, Decimal('1000.0'))
        self.assertEqual(txn.txn_type_code, 'P')
        self.assertTrue(txn.is_provisional)

    @patch('apps.integration.sync_utils.BSEStarMFClient')
    def test_sync_redemption(self, MockBSEClient):
        # Mock Response
        mock_instance = MockBSEClient.return_value
        mock_resp = MagicMock()
        mock_resp.Status = '100'

        detail = MagicMock()
        detail.OrderNo = 'ORD789'
        detail.ClientCode = 'TESTUCC'
        detail.SchemeCode = 'SCHEME1'
        detail.FolioNo = 'FOLIO99'
        detail.AllottedUnit = '5.0'
        detail.AllottedAmt = '500.0'
        detail.Nav = '100.0'
        detail.AllotmentDate = '28/10/2023'

        mock_resp.RedemptionDetails.RedemptionDetails = [detail]
        mock_instance.get_redemption_statement.return_value = mock_resp

        # Run Sync
        sync_bse_daily_reports(days=1)

        # Verify Transaction Created
        txn = Transaction.objects.filter(bse_order_id='ORD789').first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.txn_type_code, 'R')
        self.assertEqual(txn.units, Decimal('5.0'))
