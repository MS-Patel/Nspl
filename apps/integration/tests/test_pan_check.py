
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from apps.integration.bse_client import BSEStarMFClient
import json

class TestPANCheck(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_credentials = {
            'username': 'admin',
            'password': 'password123'
        }
        # Assuming we have a user created for LoginRequiredMixin
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password123'
        )
        self.client.force_login(self.user)
        self.url = reverse('integration:api_pan_check')

    @patch('apps.integration.bse_client.BSEStarMFClient._get_auth_details')
    @patch('apps.integration.bse_client.BSEStarMFClient._get_query_soap_client')
    def test_check_pan_status_success(self, mock_get_client, mock_auth):
        # Mock Auth
        mock_auth.return_value = ('encrypted_pass', 'pass_key')

        # Mock Service Response
        mock_service = MagicMock()
        mock_client_instance = MagicMock()
        mock_get_client.return_value = (mock_client_instance, mock_service)

        mock_response = MagicMock()
        mock_response.Status = '100'
        mock_response.BSERemarks = 'VALID PAN'
        mock_response.PAN = 'ABCDE1234F'
        mock_response.InvName = 'TEST INVESTOR'
        mock_service.AOFPanSearch.return_value = mock_response

        # Make Request
        response = self.client.post(
            self.url,
            json.dumps({'pan': 'ABCDE1234F'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['status'], '100')
        self.assertEqual(data['data']['remarks'], 'VALID PAN')
        self.assertEqual(data['data']['pan'], 'ABCDE1234F')
        self.assertEqual(data['data']['inv_name'], 'TEST INVESTOR')

    @patch('apps.integration.bse_client.BSEStarMFClient._get_auth_details')
    @patch('apps.integration.bse_client.BSEStarMFClient._get_query_soap_client')
    def test_check_pan_status_error(self, mock_get_client, mock_auth):
        mock_auth.return_value = ('encrypted_pass', 'pass_key')

        # Mock Service Error
        mock_service = MagicMock()
        mock_get_client.return_value = (MagicMock(), mock_service)
        mock_service.AOFPanSearch.side_effect = Exception("SOAP Error")

        response = self.client.post(
            self.url,
            json.dumps({'pan': 'ABCDE1234F'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('SOAP Error', data['remarks'])
