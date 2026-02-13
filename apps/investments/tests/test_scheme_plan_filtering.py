import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.users.factories import UserFactory
from apps.products.factories import SchemeFactory, AMCFactory

@pytest.mark.django_db
class TestSchemePlanFiltering:
    def setup_method(self):
        self.user = UserFactory(user_type='INVESTOR')
        self.client = APIClient()
        self.client.force_login(self.user)
        self.url = reverse('investments:api_order_metadata')

    def test_filter_schemes_by_plan(self):
        """Verify that schemes can be filtered by scheme_plan."""
        amc = AMCFactory()
        scheme_normal = SchemeFactory(amc=amc, scheme_plan='NORMAL', purchase_allowed=True, amc_active_flag=True)
        scheme_direct = SchemeFactory(amc=amc, scheme_plan='DIRECT', purchase_allowed=True, amc_active_flag=True)

        # Test filtering for NORMAL
        response = self.client.get(self.url, {
            'fetch_schemes': 'true',
            'amc_id': amc.id,
            'scheme_plan': 'NORMAL'
        })
        assert response.status_code == 200
        data = response.json()
        schemes = data.get('schemes', [])
        scheme_ids = [s['id'] for s in schemes]

        assert scheme_normal.id in scheme_ids
        assert scheme_direct.id not in scheme_ids

        # Test filtering for DIRECT
        response = self.client.get(self.url, {
            'fetch_schemes': 'true',
            'amc_id': amc.id,
            'scheme_plan': 'DIRECT'
        })
        assert response.status_code == 200
        data = response.json()
        schemes = data.get('schemes', [])
        scheme_ids = [s['id'] for s in schemes]

        assert scheme_direct.id in scheme_ids
        assert scheme_normal.id not in scheme_ids

    def test_filter_schemes_by_plan_empty(self):
        """Verify that passing empty scheme_plan returns all schemes for the AMC."""
        amc = AMCFactory()
        scheme_normal = SchemeFactory(amc=amc, scheme_plan='NORMAL', purchase_allowed=True, amc_active_flag=True)
        scheme_direct = SchemeFactory(amc=amc, scheme_plan='DIRECT', purchase_allowed=True, amc_active_flag=True)

        response = self.client.get(self.url, {
            'fetch_schemes': 'true',
            'amc_id': amc.id,
            'scheme_plan': ''
        })
        assert response.status_code == 200
        data = response.json()
        schemes = data.get('schemes', [])
        scheme_ids = [s['id'] for s in schemes]

        assert scheme_normal.id in scheme_ids
        assert scheme_direct.id in scheme_ids
