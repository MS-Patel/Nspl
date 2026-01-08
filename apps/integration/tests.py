from django.test import TestCase
from unittest.mock import patch, MagicMock
from apps.users.models import User, InvestorProfile, BankAccount, Nominee
from apps.integration.bse_client import BSEStarMFClient
from apps.integration.utils import map_investor_to_bse_param_string
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
            holding_nature='SI'
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

    @patch('apps.integration.bse_client.Client')
    def test_get_password_soap_success(self, MockZeepClient):
        # Mock SOAP Response
        mock_service = MagicMock()
        mock_service.getPassword.return_value = "100|EncryptedToken123"
        MockZeepClient.return_value.service = mock_service

        client = BSEStarMFClient()
        token = client._get_password()

        self.assertEqual(token, "EncryptedToken123")
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

    def test_mapper_utility(self):
        # Test if the mapper generates a string with pipes
        param_string = map_investor_to_bse_param_string(self.investor)
        self.assertIsInstance(param_string, str)
        self.assertIn('ABCDE1234F', param_string) # PAN
        self.assertIn('John', param_string) # Name
        self.assertIn('1234567890', param_string) # Account No
        self.assertIn('|', param_string)

        # Check basic count of pipes (should be large, around 80-90 fields)
        # We won't count exact because of filler fields, but should be substantial
        self.assertGreater(param_string.count('|'), 50)
