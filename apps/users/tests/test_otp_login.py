import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.users.models import User, OneTimePassword, RMProfile
from apps.users.factories import RMUserFactory, RMProfileFactory, InvestorUserFactory, InvestorProfileFactory
from django.utils import timezone
from unittest.mock import patch

@pytest.mark.django_db
class TestOTPLogin:
    def setup_method(self):
        self.client = APIClient()

    def test_send_otp_rm_success(self):
        user = RMUserFactory(username='EMP001')
        RMProfileFactory(user=user, mobile='9876543210')

        url = reverse('users:send_otp')
        with patch('apps.users.views.send_sms_with_template') as mock_sms:
            mock_sms.return_value = {'status': 'success'}
            response = self.client.post(url, {'username': 'EMP001'})

        assert response.status_code == 200
        assert response.json()['status'] == 'success'
        assert OneTimePassword.objects.filter(user=user).count() == 1
        mock_sms.assert_called_once()

    def test_send_otp_investor_success(self):
        user = InvestorUserFactory(username='ABCDE1234F')
        InvestorProfileFactory(user=user, pan='ABCDE1234F', mobile='9876543210')

        url = reverse('users:send_otp')
        with patch('apps.users.views.send_sms_with_template') as mock_sms:
            mock_sms.return_value = {'status': 'success'}
            response = self.client.post(url, {'username': 'ABCDE1234F'})

        assert response.status_code == 200
        assert response.json()['status'] == 'success'
        assert OneTimePassword.objects.filter(user=user).count() == 1

    def test_send_otp_user_not_found(self):
        url = reverse('users:send_otp')
        response = self.client.post(url, {'username': 'nonexistent'})
        assert response.status_code == 404
        assert response.json()['status'] == 'error'

    def test_verify_otp_success(self):
        user = RMUserFactory(username='EMP001')
        RMProfileFactory(user=user, mobile='9876543210')
        otp = OneTimePassword.objects.create(user=user, otp='123456')

        url = reverse('users:verify_otp_login')
        response = self.client.post(url, {'username': 'EMP001', 'otp': '123456'})

        assert response.status_code == 200
        assert response.json()['status'] == 'success'
        otp.refresh_from_db()
        assert otp.is_used is True

    def test_verify_otp_invalid(self):
        user = RMUserFactory(username='EMP001')
        RMProfileFactory(user=user, mobile='9876543210')
        OneTimePassword.objects.create(user=user, otp='123456')

        url = reverse('users:verify_otp_login')
        response = self.client.post(url, {'username': 'EMP001', 'otp': '654321'})

        assert response.status_code == 400
        assert response.json()['status'] == 'error'

    def test_verify_otp_expired(self):
        user = RMUserFactory(username='EMP001')
        RMProfileFactory(user=user, mobile='9876543210')
        expired_time = timezone.now() - timezone.timedelta(minutes=15)
        otp = OneTimePassword.objects.create(user=user, otp='123456')
        # Manually update created_at via update() as auto_now_add makes it hard to set on create
        OneTimePassword.objects.filter(id=otp.id).update(created_at=expired_time)

        url = reverse('users:verify_otp_login')
        response = self.client.post(url, {'username': 'EMP001', 'otp': '123456'})

        assert response.status_code == 400
        assert response.json()['status'] == 'error'
