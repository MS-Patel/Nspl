import pytest
from django.urls import reverse
from apps.users.factories import UserFactory, InvestorProfileFactory, DistributorProfileFactory, RMProfileFactory
from apps.products.factories import SchemeFactory
from apps.reconciliation.models import Holding
from decimal import Decimal
import factory
import json

class HoldingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Holding

    investor = factory.SubFactory(InvestorProfileFactory)
    scheme = factory.SubFactory(SchemeFactory)
    folio_number = factory.Faker('numerify', text='FOLIO#######')
    units = Decimal('100.0000')
    average_cost = Decimal('10.0000')
    current_value = Decimal('1100.00')
    current_nav = Decimal('11.0000')

@pytest.mark.django_db
class TestPortfolioInvestorListView:
    def setup_method(self):
        self.url = reverse('investments:holding_list') # Now points to PortfolioInvestorListView

    def test_admin_sees_all_investors(self, client):
        admin = UserFactory(user_type='ADMIN', is_staff=True, is_superuser=True)
        investor1 = InvestorProfileFactory()
        investor2 = InvestorProfileFactory()

        # Give them holdings
        HoldingFactory(investor=investor1, current_value=1000)
        HoldingFactory(investor=investor2, current_value=2000)

        client.force_login(admin)
        response = client.get(self.url)

        assert response.status_code == 200
        data = json.loads(response.context['grid_data_json'])
        ids = [d['id'] for d in data]
        assert investor1.id in ids
        assert investor2.id in ids

    def test_distributor_sees_own_investors(self, client):
        dist1 = DistributorProfileFactory()
        dist2 = DistributorProfileFactory()

        inv1 = InvestorProfileFactory(distributor=dist1)
        inv2 = InvestorProfileFactory(distributor=dist2)

        HoldingFactory(investor=inv1, current_value=1000)
        HoldingFactory(investor=inv2, current_value=1000)

        client.force_login(dist1.user)
        response = client.get(self.url)

        data = json.loads(response.context['grid_data_json'])
        ids = [d['id'] for d in data]

        assert inv1.id in ids
        assert inv2.id not in ids

    def test_rm_sees_assigned_investors(self, client):
        rm = RMProfileFactory()
        dist = DistributorProfileFactory(rm=rm)

        inv1 = InvestorProfileFactory(rm=rm, distributor=None) # Direct RM client
        inv2 = InvestorProfileFactory(distributor=dist) # Indirect via Distributor
        inv3 = InvestorProfileFactory() # Unrelated

        HoldingFactory(investor=inv1)
        HoldingFactory(investor=inv2)

        client.force_login(rm.user)
        response = client.get(self.url)

        data = json.loads(response.context['grid_data_json'])
        ids = [d['id'] for d in data]

        assert inv1.id in ids
        assert inv2.id in ids
        assert inv3.id not in ids

@pytest.mark.django_db
class TestInvestorPortfolioView:
    def setup_method(self):
        self.investor = InvestorProfileFactory()
        self.distributor = DistributorProfileFactory()
        self.investor.distributor = self.distributor
        self.investor.save()

        self.scheme1 = SchemeFactory(amc__name="AMC A")
        self.scheme2 = SchemeFactory(amc__name="AMC B") # Different AMC

        # Folio 1: AMC A
        HoldingFactory(
            investor=self.investor,
            scheme=self.scheme1,
            folio_number="F1",
            units=100,
            average_cost=10, # Invested 1000
            current_value=1200 # Gain 200
        )

        # Folio 2: AMC B
        HoldingFactory(
            investor=self.investor,
            scheme=self.scheme2,
            folio_number="F2",
            units=50,
            average_cost=20, # Invested 1000
            current_value=900 # Loss 100
        )

        self.url = reverse('investments:investor_portfolio', args=[self.investor.id])

    def test_access_control(self, client):
        other_dist = DistributorProfileFactory()
        client.force_login(other_dist.user)
        response = client.get(self.url)
        assert response.status_code == 404

        client.force_login(self.distributor.user)
        response = client.get(self.url)
        assert response.status_code == 200

    def test_portfolio_aggregation(self, client):
        client.force_login(self.distributor.user)
        response = client.get(self.url)

        summary = response.context['summary']
        assert summary['total_invested_value'] == 2000.0 # 1000 + 1000
        assert summary['total_current_value'] == 2100.0 # 1200 + 900
        assert summary['total_gain_loss'] == 100.0

        folio_list = json.loads(response.context['folio_list_json'])
        assert len(folio_list) == 2

        f1 = next(f for f in folio_list if f['folio_number'] == 'F1')
        assert f1['amc_name'] == "AMC A"
        assert f1['invested_value'] == 1000.0
        assert f1['current_value'] == 1200.0

        f2 = next(f for f in folio_list if f['folio_number'] == 'F2')
        assert f2['amc_name'] == "AMC B"
        assert f2['gain_loss'] == -100.0
