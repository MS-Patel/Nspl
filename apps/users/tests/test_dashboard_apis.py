import pytest
from django.urls import reverse
from rest_framework import status
from apps.users.models import User
from apps.users.factories import UserFactory, RMProfileFactory, DistributorProfileFactory, InvestorProfileFactory
from decimal import Decimal

@pytest.mark.django_db
class TestDashboardAPIs:

    def test_admin_dashboard(self, api_client):
        admin_user = UserFactory(username='admin_test', user_type=User.Types.ADMIN, is_superuser=True)
        api_client.force_authenticate(user=admin_user)

        url = reverse('users:api_admin_dashboard')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert 'rm_count' in data
        assert 'distributor_count' in data
        assert 'investor_count' in data
        assert 'total_aum' in data
        assert 'recent_orders' in data

    def test_rm_dashboard(self, api_client):
        rm_profile = RMProfileFactory()
        rm_user = rm_profile.user

        # Create a distributor linked to this RM
        dist_profile = DistributorProfileFactory(rm=rm_profile)

        # Create an investor linked to this distributor (indirectly linked to RM)
        investor_profile = InvestorProfileFactory(distributor=dist_profile, rm=rm_profile)

        api_client.force_authenticate(user=rm_user)

        url = reverse('users:api_rm_dashboard')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        # Depending on factory traits, counts might vary, but keys must exist
        assert 'distributor_count' in data
        assert 'investor_count' in data
        assert 'total_aum' in data
        assert 'recent_orders' in data

    def test_distributor_dashboard(self, api_client):
        dist_profile = DistributorProfileFactory()
        dist_user = dist_profile.user

        # Create an investor linked to this distributor
        investor_profile = InvestorProfileFactory(distributor=dist_profile)

        api_client.force_authenticate(user=dist_user)

        url = reverse('users:api_distributor_dashboard')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert 'investor_count' in data
        assert 'total_aum' in data
        assert 'active_sip_count' in data
        assert 'recent_orders' in data

    def test_investor_dashboard(self, api_client):
        investor_profile = InvestorProfileFactory()
        investor_user = investor_profile.user

        api_client.force_authenticate(user=investor_user)

        url = reverse('users:api_investor_dashboard')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert 'valuation' in data
        # Check structure of valuation
        valuation = data['valuation']
        assert 'total_current_value' in valuation
        assert 'holdings' in valuation
