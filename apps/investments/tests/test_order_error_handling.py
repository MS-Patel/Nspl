import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from apps.users.factories import UserFactory, InvestorProfileFactory
from apps.products.factories import SchemeFactory
from rest_framework.test import APIClient
from apps.investments.models import Order
from decimal import Decimal

@pytest.mark.django_db
class TestOrderCreateViewErrorHandling:
    def setup_method(self):
        self.user = UserFactory(user_type='INVESTOR')
        self.investor_profile = InvestorProfileFactory(user=self.user)
        self.client = APIClient()
        self.client.force_login(self.user)
        self.url = reverse('investments:order_create')
        self.scheme = SchemeFactory(min_purchase_amount=500, max_purchase_amount=10000)

    @patch('apps.investments.views.BSEStarMFClient')
    def test_order_submission_error_stays_on_page(self, MockBSEClient):
        # Setup Mock
        mock_client_instance = MockBSEClient.return_value
        mock_client_instance.place_order.return_value = {
            'status': 'error',
            'remarks': 'BSE Rejected: Invalid KYC'
        }

        # Valid Form Data
        data = {
            'investor': self.investor_profile.id,
            'scheme': self.scheme.id,
            'transaction_type': Order.PURCHASE,
            'amount': 1000,
            'payment_mode': 'DIRECT',
        }

        # Ensure form is valid first (investor might be hidden/handled)
        # The form __init__ for INVESTOR user forces investor field to current user profile
        # So we just need scheme and amount.

        response = self.client.post(self.url, data)

        # Assert status is 200 (Rendered) not 302 (Redirect)
        assert response.status_code == 200

        # Check if error message is in messages
        messages = list(response.context['messages'])
        assert len(messages) > 0
        assert any("BSE Error" in str(m) for m in messages)
        assert any("BSE Rejected: Invalid KYC" in str(m) for m in messages)

        # Check if form data is preserved (e.g. amount 1000)
        form = response.context['form']
        assert form.cleaned_data['amount'] == Decimal('1000')

    @patch('apps.investments.views.BSEStarMFClient')
    def test_order_submission_success_redirects(self, MockBSEClient):
        # Setup Mock
        mock_client_instance = MockBSEClient.return_value
        mock_client_instance.place_order.return_value = {
            'status': 'success',
            'bse_order_id': '12345',
            'remarks': 'Order Placed'
        }

        data = {
            'investor': self.investor_profile.id,
            'scheme': self.scheme.id,
            'transaction_type': Order.PURCHASE,
            'amount': 1000,
            'payment_mode': 'DIRECT',
        }

        response = self.client.post(self.url, data)

        # Assert status is 302 (Redirect)
        assert response.status_code == 302
        assert response.url == reverse('investments:order_list')

    @patch('apps.investments.views.BSEStarMFClient')
    def test_order_submission_exception_redirects(self, MockBSEClient):
        # Setup Mock
        mock_client_instance = MockBSEClient.return_value
        mock_client_instance.place_order.return_value = {
            'status': 'exception',
            'remarks': 'Timeout'
        }

        data = {
            'investor': self.investor_profile.id,
            'scheme': self.scheme.id,
            'transaction_type': Order.PURCHASE,
            'amount': 1000,
            'payment_mode': 'DIRECT',
        }

        response = self.client.post(self.url, data)

        # Assert status is 302 (Redirect) - Standard behavior for System Error
        assert response.status_code == 302
        assert response.url == reverse('investments:order_list')
