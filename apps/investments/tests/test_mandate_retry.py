
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from apps.investments.models import Mandate
from apps.users.factories import InvestorProfileFactory, UserFactory
from apps.investments.factories import MandateFactory

class MandateRetryTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.investor = InvestorProfileFactory(user=self.user)
        self.client = Client()
        self.client.force_login(self.user)

        self.mandate = MandateFactory(
            investor=self.investor,
            mandate_id='TEMP-12345',
            status=Mandate.PENDING
        )

    def test_is_bse_submitted_property(self):
        """Test the is_bse_submitted property logic"""
        self.assertFalse(self.mandate.is_bse_submitted)

        self.mandate.mandate_id = 'UMRN12345'
        self.mandate.save()
        self.assertTrue(self.mandate.is_bse_submitted)

    @patch('apps.investments.views.BSEStarMFClient')
    def test_retry_success(self, MockBSEClient):
        """Test successful retry of mandate submission"""
        # Mock BSE Client response
        mock_instance = MockBSEClient.return_value
        mock_instance.register_mandate.return_value = {
            'status': 'success',
            'mandate_id': 'NEW-UMRN-123',
            'remarks': 'Success'
        }

        # Reset mandate to TEMP
        self.mandate.mandate_id = 'TEMP-12345'
        self.mandate.save()

        url = reverse('investments:mandate_retry', args=[self.mandate.pk])
        response = self.client.post(url)

        # Check redirect
        self.assertRedirects(response, reverse('users:investor_detail', args=[self.investor.pk]))

        # Check DB update
        self.mandate.refresh_from_db()
        self.assertEqual(self.mandate.mandate_id, 'NEW-UMRN-123')
        self.assertEqual(self.mandate.status, Mandate.PENDING) # Still Pending waiting for auth
        self.assertTrue(self.mandate.is_bse_submitted)

    @patch('apps.investments.views.BSEStarMFClient')
    def test_retry_failure_exception(self, MockBSEClient):
        """Test retry failure (exception scenario)"""
        mock_instance = MockBSEClient.return_value
        mock_instance.register_mandate.return_value = {
            'status': 'exception',
            'remarks': 'Network Error'
        }

        url = reverse('investments:mandate_retry', args=[self.mandate.pk])
        response = self.client.post(url)

        self.assertRedirects(response, reverse('users:investor_detail', args=[self.investor.pk]))

        self.mandate.refresh_from_db()
        self.assertTrue(self.mandate.mandate_id.startswith('TEMP-'))
        self.assertEqual(self.mandate.status, Mandate.PENDING)

    @patch('apps.investments.views.BSEStarMFClient')
    def test_retry_failure_rejected(self, MockBSEClient):
        """Test retry failure (rejected scenario)"""
        mock_instance = MockBSEClient.return_value
        mock_instance.register_mandate.return_value = {
            'status': 'error',
            'remarks': 'Invalid Data'
        }

        url = reverse('investments:mandate_retry', args=[self.mandate.pk])
        response = self.client.post(url)

        self.assertRedirects(response, reverse('users:investor_detail', args=[self.investor.pk]))

        self.mandate.refresh_from_db()
        self.assertEqual(self.mandate.status, Mandate.REJECTED)

    def test_unauthorized_access(self):
        """Test access control"""
        other_investor = InvestorProfileFactory()
        self.client.force_login(other_investor.user)

        url = reverse('investments:mandate_retry', args=[self.mandate.pk])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)

    def test_retry_on_submitted_mandate(self):
        """Test preventing retry on already submitted mandate"""
        self.mandate.mandate_id = 'REAL-ID'
        self.mandate.save()

        url = reverse('investments:mandate_retry', args=[self.mandate.pk])
        response = self.client.post(url, follow=True)

        # Should redirect with warning message
        messages = list(response.context['messages'])
        self.assertTrue(any("cannot be retried" in str(m) for m in messages))
