import json
from unittest.mock import patch
from django.test import Client, TestCase
from django.urls import reverse

class GetBankDetailsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('integration:api_bank_details')

    @patch('apps.integration.views.requests.get')
    def test_get_bank_details_success(self, mock_get):
        # Mock successful response from Razorpay
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'BANK': 'HDFC Bank',
            'BRANCH': 'MUMBAI',
            'CITY': 'MUMBAI',
            'STATE': 'MAHARASHTRA',
            'IFSC': 'HDFC0000123'
        }

        response = self.client.get(self.url, {'ifsc': 'HDFC0000123'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['BANK'], 'HDFC Bank')
        self.assertEqual(data['data']['IFSC'], 'HDFC0000123')

    @patch('apps.integration.views.requests.get')
    def test_get_bank_details_invalid_ifsc_api(self, mock_get):
        # Mock 404 response from API (valid format, invalid code)
        mock_response = mock_get.return_value
        mock_response.status_code = 404

        response = self.client.get(self.url, {'ifsc': 'HDFC0000999'})

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], 'Invalid IFSC Code.')

    def test_get_bank_details_invalid_format(self):
        # Test regex validation (Invalid format)
        response = self.client.get(self.url, {'ifsc': 'INVALID123'}) # Too long/short or wrong chars

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], 'Invalid IFSC Code format.')

    def test_get_bank_details_missing_param(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], 'IFSC code is required.')
