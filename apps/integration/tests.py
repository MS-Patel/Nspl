from django.test import TestCase
from unittest.mock import patch, MagicMock
from apps.users.models import User, InvestorProfile, BankAccount, Nominee
from apps.integration.bse_client import BSEStarMFClient
from apps.integration.utils import map_investor_to_bse_param_string
from apps.investments.models import Order, Folio
from apps.products.models import Scheme, AMC, SchemeCategory
import datetime

class BSEClientTest(TestCase):
    def setUp(self):
        # Create user and investor
        self.user = User.objects.create_user(username='testinv', password='password', first_name='John', last_name='Doe')
        self.investor = InvestorProfile.objects.create(
            user=self.user,
            pan='ABCDE1234F',
            dob=datetime.date(1990, 1, 1),
            gender='M',
            mobile='9876543210',
            email='john@example.com',
            address_1='Flat 101',
            city='Mumbai',
            state='MA', # Using code for simplicity in test
            pincode='400001',
            tax_status='01',
            occupation='01',
            holding_nature='SI',
            ucc_code='TEST001'
        )
        self.bank = BankAccount.objects.create(
            investor=self.investor,
            ifsc_code='HDFC0000123',
            account_number='1234567890',
            bank_name='HDFC Bank',
            is_default=True
        )
        self.nominee = Nominee.objects.create(
            investor=self.investor,
            name='Jane Doe',
            relationship='SP', # Spouse Code
            percentage=100.00
        )

        # Setup Product Data
        self.amc = AMC.objects.create(name='Test AMC')
        self.cat = SchemeCategory.objects.create(name='Equity')
        self.scheme = Scheme.objects.create(
            amc=self.amc,
            category=self.cat,
            name='Test Scheme',
            scheme_code='SCHEME001',
            isin='ISIN001',
            min_purchase_amount=1000,
            purchase_allowed=True
        )

    @patch('apps.integration.bse_client.Client')
    def test_get_password_soap_success(self, MockZeepClient):
        # Mock SOAP Response
        mock_service = MagicMock()
        mock_service.getPassword.return_value = "100|EncryptedToken123"
        MockZeepClient.return_value.service = mock_service

        client = BSEStarMFClient()
        token = client._get_password() # Should return string only

        self.assertEqual(token, "EncryptedToken123")
        mock_service.getPassword.assert_called_once()

    @patch('apps.integration.bse_client.Client')
    def test_get_auth_details_success(self, MockZeepClient):
        # Mock SOAP Response
        mock_service = MagicMock()
        mock_service.getPassword.return_value = "100|EncryptedToken123"
        MockZeepClient.return_value.service = mock_service

        client = BSEStarMFClient()
        token, pass_key = client._get_auth_details() # Should return tuple

        self.assertEqual(token, "EncryptedToken123")
        self.assertIsNotNone(pass_key)
        self.assertEqual(len(pass_key), 10)
        mock_service.getPassword.assert_called_once()

    @patch('apps.integration.bse_client.requests.post')
    def test_register_client_success(self, mock_post):
        # Mock JSON Response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Status": "0",
            "Remarks": "CLIENT REGISTERED SUCCESSFULLY"
        }
        mock_post.return_value = mock_response

        client = BSEStarMFClient()
        # Create payload using our utility
        param_string = map_investor_to_bse_param_string(self.investor)
        payload = {'Param': param_string}

        result = client.register_client(payload)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['remarks'], 'CLIENT REGISTERED SUCCESSFULLY')
        mock_post.assert_called_once()

    @patch('apps.integration.bse_client.Client')
    def test_place_order_success(self, MockZeepClient):
        # Create Order (Purchase)
        order = Order.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            amount=5000,
            transaction_type=Order.PURCHASE,
            is_new_folio=True
        )

        # Mock Service
        mock_service = MagicMock()
        mock_service.getPassword.return_value = "100|EncryptedToken123"
        mock_service.orderEntryParam.return_value = "0|123456|Order Placed Successfully"

        MockZeepClient.return_value.service = mock_service

        client = BSEStarMFClient()
        result = client.place_order(order)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['bse_order_id'], '123456')

        # Verify calls
        mock_service.getPassword.assert_called_once()
        mock_service.orderEntryParam.assert_called_once()

        call_args = mock_service.orderEntryParam.call_args[1]
        self.assertEqual(call_args['ClientCode'], 'TEST001')
        self.assertEqual(call_args['SchemeCode'], 'SCHEME001')
        self.assertEqual(call_args['TxtAmount'], '5000.00')
        self.assertEqual(call_args['TxtQuantity'], '0')

    @patch('apps.integration.bse_client.Client')
    def test_place_redemption_with_decimals(self, MockZeepClient):
        # Create Order (Redemption with decimals)
        order = Order.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            amount=0,
            units=10.5567,
            transaction_type=Order.REDEMPTION,
            is_new_folio=False
        )

        # Mock Service
        mock_service = MagicMock()
        mock_service.getPassword.return_value = "100|EncryptedToken123"
        mock_service.orderEntryParam.return_value = "0|123456|Redemption Placed"

        MockZeepClient.return_value.service = mock_service

        client = BSEStarMFClient()
        result = client.place_order(order)

        self.assertEqual(result['status'], 'success')

        call_args = mock_service.orderEntryParam.call_args[1]
        self.assertEqual(call_args['TxtQuantity'], '10.5567')

    def test_mapper_utility(self):
        # Test if the mapper generates a string with pipes
        param_string = map_investor_to_bse_param_string(self.investor)
        self.assertIsInstance(param_string, str)
        self.assertIn('ABCDE1234F', param_string) # PAN
        self.assertIn('|', param_string)
