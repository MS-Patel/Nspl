import pytest
import factory
from django.urls import reverse
from apps.users.factories import UserFactory, InvestorProfileFactory, DistributorProfileFactory
from apps.products.factories import SchemeFactory, AMCFactory
from apps.reconciliation.models import Holding, Transaction
from decimal import Decimal

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

class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transaction

    investor = factory.SubFactory(InvestorProfileFactory)
    scheme = factory.SubFactory(SchemeFactory)
    folio_number = factory.Faker('numerify', text='FOLIO#######')
    txn_number = factory.Sequence(lambda n: f'TXN{n:08d}')
    date = factory.Faker('date_this_year')
    amount = Decimal('1000.00')
    units = Decimal('100.0000')
    txn_type_code = 'P'

@pytest.mark.django_db
class TestFolioDetailView:

    def test_access_denied_for_anonymous(self, client):
        url = reverse('investments:folio_detail', kwargs={'folio_number': '123'})
        response = client.get(url)
        assert response.status_code == 302 # Login required

    def test_folio_detail_investor_access(self, client):
        investor_profile = InvestorProfileFactory()
        user = investor_profile.user
        client.force_login(user)

        scheme = SchemeFactory()
        folio_number = 'FOL123'

        # Create Holding
        HoldingFactory(
            investor=investor_profile,
            scheme=scheme,
            folio_number=folio_number,
            units=100,
            average_cost=10,
            current_value=1200 # Gain 200
        )

        # Create Transactions
        TransactionFactory(
            investor=investor_profile,
            scheme=scheme,
            folio_number=folio_number,
            amount=1000,
            units=100,
            txn_type_code='P'
        )

        url = reverse('investments:folio_detail', kwargs={'folio_number': folio_number})
        response = client.get(url)

        assert response.status_code == 200
        assert response.context['folio_number'] == folio_number
        assert response.context['summary']['total_current_value'] == 1200
        assert response.context['summary']['total_invested_value'] == 1000 # 100 * 10
        assert response.context['summary']['total_gain_loss'] == 200

        fund_data = response.context['fund_data']
        assert len(fund_data) == 1
        assert fund_data[0]['scheme'] == scheme
        assert len(fund_data[0]['transactions']) == 1

    def test_folio_detail_other_investor_denied(self, client):
        investor1 = InvestorProfileFactory()
        investor2 = InvestorProfileFactory() # Attacker

        folio_number = 'FOL123'
        HoldingFactory(investor=investor1, folio_number=folio_number)

        client.force_login(investor2.user)
        url = reverse('investments:folio_detail', kwargs={'folio_number': folio_number})

        # Should return 404 as queryset filters out other investors
        response = client.get(url)
        assert response.status_code == 404

    def test_folio_detail_distributor_access(self, client):
        distributor = DistributorProfileFactory()
        investor = InvestorProfileFactory(distributor=distributor)

        folio_number = 'FOL123'
        HoldingFactory(investor=investor, folio_number=folio_number)

        client.force_login(distributor.user)
        url = reverse('investments:folio_detail', kwargs={'folio_number': folio_number})

        response = client.get(url)
        assert response.status_code == 200

    def test_folio_detail_other_distributor_denied(self, client):
        dist1 = DistributorProfileFactory()
        dist2 = DistributorProfileFactory()
        investor = InvestorProfileFactory(distributor=dist1)

        folio_number = 'FOL123'
        HoldingFactory(investor=investor, folio_number=folio_number)

        client.force_login(dist2.user)
        url = reverse('investments:folio_detail', kwargs={'folio_number': folio_number})

        response = client.get(url)
        assert response.status_code == 404
