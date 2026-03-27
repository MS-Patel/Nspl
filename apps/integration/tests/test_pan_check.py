
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

    @patch('apps.integration.cvl_client.CVLClient.get_pan_status')
    def test_check_pan_status_success(self, mock_get_pan_status):
        # Mock Service Response
        mock_get_pan_status.return_value = {
            'status': 'success',
            'data': {
                'name': 'TEST INVESTOR',
                'status': 'Verified',
                'raw': 'TEST RAW XML'
            }
        }

        # Make Request
        response = self.client.post(
            self.url,
            json.dumps({'pan': 'ABCDE1234F'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['status'], 'Verified')
        self.assertEqual(data['data']['name'], 'TEST INVESTOR')

    @patch('apps.integration.cvl_client.CVLClient.get_pan_status')
    def test_check_pan_status_error(self, mock_get_pan_status):
        # Mock Service Error
        mock_get_pan_status.side_effect = Exception("SOAP Error")

        response = self.client.post(
            self.url,
            json.dumps({'pan': 'ABCDE1234F'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('SOAP Error', data['remarks'])
