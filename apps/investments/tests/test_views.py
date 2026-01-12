import pytest
from django.urls import reverse
from apps.users.factories import UserFactory, InvestorProfileFactory, DistributorProfileFactory, RMProfileFactory
from apps.products.factories import SchemeFactory, AMCFactory, SchemeCategoryFactory
from apps.investments.models import Order
from apps.investments.factories import MandateFactory, FolioFactory
from rest_framework.test import APIClient
from decimal import Decimal

@pytest.mark.django_db
class TestOrderCreateView:
    def setup_method(self):
        self.user = UserFactory(user_type='INVESTOR')
        # Ensure profile exists as it's often checked in views
        self.investor_profile = InvestorProfileFactory(user=self.user)
        self.client = APIClient()
        self.client.force_login(self.user)
        self.url = reverse('investments:order_create')

    def test_view_loads_with_default_transaction_type(self):
        response = self.client.get(self.url)
        assert response.status_code == 200
        form = response.context['form']
        # Check initial data contains Purchase default
        assert form.initial.get('transaction_type') == Order.PURCHASE

@pytest.mark.django_db
class TestOrderMetadataAPI:
    def setup_method(self):
        self.user = UserFactory(user_type='INVESTOR')
        self.investor_profile = InvestorProfileFactory(user=self.user)
        self.client = APIClient()
        self.client.force_login(self.user)
        self.url = reverse('investments:api_order_metadata')

    def test_fetch_schemes_structure(self):
        amc = AMCFactory()
        cat = SchemeCategoryFactory()
        scheme = SchemeFactory(amc=amc, category=cat, purchase_allowed=True)

        response = self.client.get(self.url, {'fetch_schemes': 'true', 'amc_id': amc.id})
        assert response.status_code == 200
        data = response.json()

        assert 'schemes' in data
        assert len(data['schemes']) == 1
        s = data['schemes'][0]
        assert s['id'] == scheme.id
        assert s['name'] == scheme.name
        # Verify fields needed for TomSelect
        assert 'id' in s
        assert 'name' in s
        assert 'scheme_code' in s

    def test_fetch_scheme_details(self):
        scheme = SchemeFactory(min_purchase_amount=5000)
        response = self.client.get(self.url, {'scheme_id': scheme.id})
        assert response.status_code == 200
        data = response.json()

        assert 'scheme_details' in data
        # JSON serializes decimals as strings sometimes, or we compare values loosely
        assert float(data['scheme_details']['min_purchase_amount']) == 5000.0

    def test_fetch_mandates(self):
        mandate = MandateFactory(investor=self.investor_profile, status='APPROVED')
        # We need to verify as the investor
        response = self.client.get(self.url, {'investor_id': self.investor_profile.id})
        assert response.status_code == 200
        data = response.json()

        assert 'mandates' in data
        assert len(data['mandates']) == 1
        assert data['mandates'][0]['id'] == mandate.id

@pytest.mark.django_db
class TestFolioAPI:
    def setup_method(self):
        self.user = UserFactory(user_type='INVESTOR')
        self.investor_profile = InvestorProfileFactory(user=self.user)
        self.client = APIClient()
        self.client.force_login(self.user)
        self.url = reverse('investments:api_folios')

    def test_fetch_folios(self):
        folio = FolioFactory(investor=self.investor_profile)
        response = self.client.get(self.url, {'investor_id': self.investor_profile.id})
        assert response.status_code == 200
        data = response.json()

        assert 'folios' in data
        assert len(data['folios']) == 1
        assert data['folios'][0]['id'] == folio.id
