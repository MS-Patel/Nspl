import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.users.factories import RMProfileFactory, DistributorProfileFactory, InvestorUserFactory, UserFactory

User = get_user_model()

@pytest.mark.django_db
class TestAuthenticationIntegration:
    def test_login_redirects(self, client):
        # Admin Login
        admin = User.objects.create_superuser(username='admin', password='password', user_type=User.Types.ADMIN)
        response = client.post(
            reverse('users:api_login'),
            {'username': 'admin', 'password': 'password'},
            content_type='application/json'
        )
        assert response.status_code == 200
        assert response.json()['status'] == 'success'
        assert response.json()['redirect_url'] == reverse('users:admin_dashboard')
        client.logout()

        # RM Login
        rm_profile = RMProfileFactory(user__password='password')
        response = client.post(
            reverse('users:api_login'),
            {'username': rm_profile.user.username, 'password': 'password'},
            content_type='application/json'
        )
        assert response.status_code == 200
        assert response.json()['status'] == 'success'
        assert response.json()['redirect_url'] == reverse('users:rm_dashboard')
        client.logout()

        # Distributor Login
        dist_profile = DistributorProfileFactory(user__password='password')
        response = client.post(
            reverse('users:api_login'),
            {'username': dist_profile.user.username, 'password': 'password'},
            content_type='application/json'
        )
        assert response.status_code == 200
        assert response.json()['status'] == 'success'
        assert response.json()['redirect_url'] == reverse('users:distributor_dashboard')
        client.logout()

        # Investor Login
        investor_user = InvestorUserFactory(password='password')
        response = client.post(
            reverse('users:api_login'),
            {'username': investor_user.username, 'password': 'password'},
            content_type='application/json'
        )
        assert response.status_code == 200
        assert response.json()['status'] == 'success'
        assert response.json()['redirect_url'] == reverse('users:investor_dashboard')
        client.logout()

    def test_navigation_menu_visibility(self, client):
        # Admin should see RM and Distributor links
        admin = User.objects.create_superuser(username='admin', password='password', user_type=User.Types.ADMIN)
        client.force_login(admin)
        response = client.get(reverse('users:admin_dashboard'))
        assert response.status_code == 200
        assert b'Masters' in response.content
        assert reverse('users:rm_list') in str(response.content)

        # Distributor should NOT see Masters dropdown
        dist_profile = DistributorProfileFactory()
        assert dist_profile.user.user_type == 'DISTRIBUTOR'
        assert dist_profile.user.is_staff is False

        client.force_login(dist_profile.user)
        response = client.get(reverse('users:distributor_dashboard'))

        # Ensure the menu item "Masters" (the dropdown toggle) is not present
        assert b'<span class="text-xs-plus">Masters</span>' not in response.content
        assert b'id="master-menu-dropdown"' not in response.content

@pytest.mark.django_db
class TestFormValidation:
    def test_password_mismatch(self, client):
        admin = User.objects.create_superuser(username='admin', password='password', user_type=User.Types.ADMIN)
        client.force_login(admin)

        url = reverse('users:rm_create')
        data = {
            'username': 'rm_fail',
            'email': 'rm_fail@example.com',
            'name': 'RM Fail',
            'password': 'password123',
            'confirm_password': 'password456', # Mismatch
            'employee_code': 'EMP000'
        }
        response = client.post(url, data)
        assert response.status_code == 200 # Form invalid re-renders page
        form = response.context['form']
        assert not form.is_valid()
        assert "passwords do not match" in str(form.non_field_errors())

    def test_required_fields(self, client):
        admin = User.objects.create_superuser(username='admin', password='password', user_type=User.Types.ADMIN)
        client.force_login(admin)

        url = reverse('users:distributor_create')
        data = {
            'username': 'dist_fail',
            # Missing fields
        }
        response = client.post(url, data)
        form = response.context['form']
        assert not form.is_valid()
        assert 'arn_number' in form.errors

@pytest.mark.django_db
def test_react_app_loads(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'<div id="root">' in response.content

    response = client.get('/login/')
    assert response.status_code == 200
    assert b'<div id="root">' in response.content
