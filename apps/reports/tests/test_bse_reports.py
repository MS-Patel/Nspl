from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from apps.users.models import User, InvestorProfile
from apps.integration.bse_client import BSEStarMFClient
import datetime

class BSEReportViewsTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(username='testuser', password='password', user_type=User.Types.INVESTOR)
        self.investor = InvestorProfile.objects.create(user=self.user, pan='ABCDE1234F', ucc_code='TESTUCC')
        self.client.login(username='testuser', password='password')

    @patch('apps.reports.views.BSEStarMFClient')
    def test_order_status_report(self, MockBSEClient):
        # Setup Mock
        mock_instance = MockBSEClient.return_value
        mock_response = MagicMock()
        mock_response.Status = '0'

        # Mock Order Details
        detail = MagicMock()
        detail.OrderNo = '12345'
        detail.ClientCode = 'TESTUCC'
        detail.SchemeCode = 'SCHEME1'
        detail.OrderType = 'Purchase'
        detail.BuySell = 'P'
        detail.OrderVal = '1000'
        detail.OrderStatus = 'Approved'
        detail.OrderRemarks = 'Success'
        detail.TransNo = 'T123'

        mock_response.OrderDetails = [detail]
        mock_instance.get_order_status.return_value = mock_response

        # Request
        url = reverse('reports:order_status_report')
        response = self.client.get(url, {'from_date': '01/01/2024', 'to_date': '31/01/2024'})

        # Verify
        self.assertEqual(response.status_code, 200)
        # Check if get_order_status was called with correct params
        mock_instance.get_order_status.assert_called_with(
            from_date='01/01/2024',
            to_date='31/01/2024',
            client_code='TESTUCC'
        )
        # Check context data
        self.assertIn('grid_data_json', response.context)
        self.assertIn('12345', response.context['grid_data_json'])
        self.assertIn('Approved', response.context['grid_data_json'])

    @patch('apps.reports.views.BSEStarMFClient')
    def test_allotment_report(self, MockBSEClient):
        mock_instance = MockBSEClient.return_value
        mock_response = MagicMock()
        mock_response.Status = '0'

        detail = MagicMock()
        detail.OrderNo = '54321'
        detail.ClientCode = 'TESTUCC'
        detail.SchemeCode = 'SCHEME2'
        detail.FolioNo = 'FOLIO1'
        detail.AllottedUnit = '10.5'
        detail.AllottedAmt = '1000'
        detail.Nav = '100'
        detail.AllotmentDate = '15/01/2024'
        detail.TransNo = 'T123'

        mock_response.AllotmentDetails = [detail]
        mock_instance.get_allotment_statement.return_value = mock_response

        url = reverse('reports:allotment_report')
        response = self.client.get(url, {'from_date': '01/01/2024', 'to_date': '31/01/2024'})

        self.assertEqual(response.status_code, 200)
        mock_instance.get_allotment_statement.assert_called_with(
            from_date='01/01/2024',
            to_date='31/01/2024',
            client_code='TESTUCC',
            order_type='Purchase'
        )
        self.assertIn('54321', response.context['grid_data_json'])

    @patch('apps.reports.views.BSEStarMFClient')
    def test_redemption_report(self, MockBSEClient):
        mock_instance = MockBSEClient.return_value
        mock_response = MagicMock()
        mock_response.Status = '0'

        detail = MagicMock()
        detail.OrderNo = '98765'
        detail.ClientCode = 'TESTUCC'
        detail.SchemeCode = 'SCHEME3' # Added SchemeCode which is accessed
        detail.FolioNo = 'FOLIO2' # Added FolioNo
        detail.AllottedUnit = '50'
        detail.AllottedAmt = '5000'
        detail.Nav = '100'
        detail.AllotmentDate = '20/01/2024'
        detail.TransNo = 'T456'

        mock_response.AllotmentDetails = [detail]
        mock_instance.get_redemption_statement.return_value = mock_response

        url = reverse('reports:redemption_report')
        response = self.client.get(url, {'from_date': '01/01/2024', 'to_date': '31/01/2024'})

        self.assertEqual(response.status_code, 200)
        mock_instance.get_redemption_statement.assert_called_with(
            from_date='01/01/2024',
            to_date='31/01/2024',
            client_code='TESTUCC'
        )
        self.assertIn('98765', response.context['grid_data_json'])
