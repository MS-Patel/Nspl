import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.users.models import RMProfile, DistributorProfile
from apps.users.factories import UserFactory, RMProfileFactory, DistributorProfileFactory

User = get_user_model()

@pytest.mark.django_db
class TestProfileView:
    def test_profile_view_access(self, client):
        user = UserFactory()
        client.force_login(user)
        url = reverse('users:profile')
        response = client.get(url)
        assert response.status_code == 200
        assert 'user_form' in response.context

    def test_update_user_profile(self, client):
        user = UserFactory()
        client.force_login(user)
        url = reverse('users:profile')
        data = {
            'name': 'Updated Name',
            'email': 'updated@example.com'
        }
        response = client.post(url, data)
        assert response.status_code == 302
        user.refresh_from_db()
        assert user.name == 'Updated Name'
        assert user.email == 'updated@example.com'

    def test_rm_profile_update(self, client):
        rm = RMProfileFactory()
        client.force_login(rm.user)
        url = reverse('users:profile')

        # RM specific fields are disabled in form but should be present in context
        response = client.get(url)
        assert 'profile_form' in response.context
        assert response.context['profile_form'].instance == rm

        # Try updating name (User) and ensure profile form is also validated/saved (even if readonly)
        data = {
            'name': 'Updated RM',
            'email': rm.user.email,
            'employee_code': rm.employee_code, # Readonly field sent back
            'branch': rm.branch.pk if rm.branch else ''
        }
        response = client.post(url, data)
        assert response.status_code == 302
        rm.user.refresh_from_db()
        assert rm.user.name == 'Updated RM'

    def test_distributor_profile_update(self, client):
        dist = DistributorProfileFactory()
        client.force_login(dist.user)
        url = reverse('users:profile')

        response = client.get(url)
        assert 'profile_form' in response.context

        data = {
            'name': 'Updated Dist',
            'email': dist.user.email,
            'arn_number': dist.arn_number,
            'mobile': '1234567890',
            'euin': 'E123456',
            'pan': 'ABCDE1234F'
        }
        response = client.post(url, data)
        assert response.status_code == 302
        dist.refresh_from_db()
        assert dist.mobile == '1234567890'
        assert dist.euin == 'E123456'

@pytest.mark.django_db
class TestPasswordChange:
    def test_password_change_view(self, client):
        user = UserFactory(password='oldpassword')
        client.force_login(user)
        url = reverse('users:password_change')

        response = client.get(url)
        assert response.status_code == 200

        data = {
            'old_password': 'oldpassword',
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert response.url == reverse('users:profile')

        user.refresh_from_db()
        assert user.check_password('newpassword123')

@pytest.mark.django_db
class TestPasswordReset:
    def test_password_reset_view(self, client):
        url = reverse('users:password_reset')
        response = client.get(url)
        assert response.status_code == 200

        user = UserFactory(email='reset@example.com')
        data = {'email': 'reset@example.com'}
        response = client.post(url, data)
        assert response.status_code == 302
        assert response.url == reverse('users:password_reset_done')
