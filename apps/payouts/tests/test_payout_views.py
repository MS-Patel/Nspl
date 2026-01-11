import pytest
from django.urls import reverse
from datetime import date
from decimal import Decimal
from apps.users.models import User
from apps.payouts.models import Payout, PayoutDetail

@pytest.fixture
def distributor_user(db):
    user = User.objects.create_user(
        username='distributor1',
        password='password123',
        user_type=User.Types.DISTRIBUTOR,
        email='dist1@example.com'
    )
    return user

@pytest.fixture
def other_distributor_user(db):
    user = User.objects.create_user(
        username='distributor2',
        password='password123',
        user_type=User.Types.DISTRIBUTOR,
        email='dist2@example.com'
    )
    return user

@pytest.fixture
def payout(db, distributor_user):
    payout = Payout.objects.create(
        distributor=distributor_user,
        period_date=date(2023, 10, 1),
        total_aum=Decimal('100000.00'),
        total_commission=Decimal('500.00'),
        status=Payout.STATUS_PAID
    )
    PayoutDetail.objects.create(
        payout=payout,
        investor_name="Inv 1",
        scheme_name="Scheme A",
        aum=Decimal('50000'),
        applied_rate=Decimal('0.5'),
        commission_amount=Decimal('250')
    )
    return payout

@pytest.mark.django_db
class TestPayoutViews:

    def test_payout_list_view(self, client, distributor_user, payout):
        client.force_login(distributor_user)
        url = reverse('payout_list')
        response = client.get(url)
        assert response.status_code == 200
        assert 'grid_data_json' in response.context
        assert 'October 2023' in response.content.decode()

    def test_payout_detail_view(self, client, distributor_user, payout):
        client.force_login(distributor_user)
        url = reverse('payout_detail', kwargs={'pk': payout.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert 'grid_data_json' in response.context
        assert 'Inv 1' in response.content.decode()

    def test_payout_export_view(self, client, distributor_user, payout):
        client.force_login(distributor_user)
        url = reverse('payout_export', kwargs={'pk': payout.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert f'Payout_2023_10.xlsx' in response['Content-Disposition']

    def test_access_denied_for_other_distributor(self, client, other_distributor_user, payout):
        client.force_login(other_distributor_user)
        # Try to access detail of first distributor's payout
        url = reverse('payout_detail', kwargs={'pk': payout.pk})
        response = client.get(url)
        assert response.status_code == 404  # Should be 404 because of filter in get_queryset

        # Try to export
        url = reverse('payout_export', kwargs={'pk': payout.pk})
        response = client.get(url)
        assert response.status_code == 404

    def test_access_denied_for_anonymous(self, client, payout):
        url = reverse('payout_list')
        response = client.get(url)
        assert response.status_code == 302 # Redirect to login

        url = reverse('payout_detail', kwargs={'pk': payout.pk})
        response = client.get(url)
        assert response.status_code == 302
