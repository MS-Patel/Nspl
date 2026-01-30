from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from apps.integration.cvl_client import CVLClient
from django.contrib.auth import get_user_model
from apps.users.models import InvestorProfile
import json

User = get_user_model()

class TestCVLPANCheck(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password123'
        )
        self.client.force_login(self.user)
        self.url = reverse('integration:api_pan_check')

    @patch('apps.integration.cvl_client.CVLClient._get_auth_details')
    @patch('apps.integration.cvl_client.CVLClient._get_soap_client')
    def test_client_get_pan_status_success(self, mock_get_client, mock_auth):
        """Test CVLClient.get_pan_status logic directly"""
        mock_auth.return_value = ('encrypted_pass', 'pass_key')
        
        mock_service = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_instance.service = mock_service
        mock_get_client.return_value = mock_client_instance

        # Mock Response (Pipe separated)
        mock_service.GetPanStatus.return_value = "1|JOHN DOE|VERIFIED"

        client = CVLClient()
        result = client.get_pan_status("ABCDE1234F")

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['data']['name'], 'JOHN DOE')
        self.assertEqual(result['data']['status'], 'VERIFIED')

    @patch('apps.integration.cvl_client.CVLClient._get_auth_details')
    @patch('apps.integration.cvl_client.CVLClient._get_soap_client')
    def test_client_get_pan_status_json(self, mock_get_client, mock_auth):
        """Test CVLClient.get_pan_status with JSON response"""
        mock_auth.return_value = ('encrypted_pass', 'pass_key')
        
        mock_service = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_instance.service = mock_service
        mock_get_client.return_value = mock_client_instance

        # Mock Response (JSON)
        mock_service.GetPanStatus.return_value = '{"APP_NAME": "JANE DOE", "APP_STATUS": "Active"}'

        client = CVLClient()
        result = client.get_pan_status("ABCDE1234F")

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['data']['name'], 'JANE DOE')
        self.assertEqual(result['data']['status'], 'Active')

    @patch('apps.integration.views.CVLClient')
    def test_view_local_user_exists(self, MockCVLClient):
        """Test that view returns error if PAN exists as User"""
        # Create a user with PAN as username
        User.objects.create_user(username='ABCDE1234F', password='pw')

        response = self.client.post(
            self.url,
            json.dumps({'pan': 'ABCDE1234F'}),
            content_type='application/json'
        )
        
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('already registered', data['remarks'])
        MockCVLClient.assert_not_called()

    @patch('apps.integration.views.CVLClient')
    def test_view_local_investor_exists(self, MockCVLClient):
        """Test that view returns error if PAN exists in InvestorProfile"""
        # Create user + investor
        u = User.objects.create_user(username='testuser', password='pw')
        InvestorProfile.objects.create(user=u, pan='ABCDE1234F', dob='1990-01-01', mobile='9999999999')

        response = self.client.post(
            self.url,
            json.dumps({'pan': 'ABCDE1234F'}),
            content_type='application/json'
        )
        
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('Investor Profile with PAN', data['remarks'])
        MockCVLClient.assert_not_called()

    @patch('apps.integration.views.CVLClient')
    def test_view_pan_check_success(self, MockCVLClient):
        """Test successful PAN check via View"""
        mock_instance = MockCVLClient.return_value
        mock_instance.get_pan_status.return_value = {
            'status': 'success',
            'data': {'name': 'NEW INVESTOR', 'status': 'OK'}
        }

        response = self.client.post(
            self.url,
            json.dumps({'pan': 'ZZZZZ1234Z'}),
            content_type='application/json'
        )
        
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['name'], 'NEW INVESTOR')
