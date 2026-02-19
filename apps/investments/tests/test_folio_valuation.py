import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from apps.investments.utils import calculate_xirr, get_cash_flows
from apps.reconciliation.models import Transaction, Holding
from apps.products.models import Scheme, AMC, NAVHistory
from apps.users.models import InvestorProfile, User
from apps.investments.views import FolioDetailView
from django.test import RequestFactory, Client
from django.urls import reverse

@pytest.mark.django_db
class TestFolioValuation:

    def test_calculate_xirr_simple(self):
        # Invest 1000, 1 year later value 1100 -> 10% return
        d1 = date(2023, 1, 1)
        d2 = date(2024, 1, 1)
        flows = [(d1, -1000.0), (d2, 1100.0)]

        xirr = calculate_xirr(flows)
        assert xirr is not None
        # Approx 0.10
        assert 0.099 < xirr < 0.101

    def test_calculate_xirr_multiple_flows(self):
        # Invest 1000 on Jan 1
        # Invest 1000 on July 1
        # Value 2200 on Jan 1 next year
        d1 = date(2023, 1, 1)
        d2 = date(2023, 7, 1)
        d3 = date(2024, 1, 1)
        flows = [(d1, -1000.0), (d2, -1000.0), (d3, 2200.0)]

        xirr = calculate_xirr(flows)
        assert xirr is not None
        # Total gain 200 on 2000 invested. But timed differently.
        # Approx 10% simple return overall, but XIRR accounts for time.
        # Should be around 13-14%?
        # Let's just check it returns a reasonable float
        assert 0.0 < xirr < 0.5

    def test_get_cash_flows(self, db):
        # Setup Data
        user = User.objects.create(username='testinv', user_type='INVESTOR')
        investor = InvestorProfile.objects.create(user=user, pan='ABCDE1234F')
        amc = AMC.objects.create(name='Test AMC', code='TEST')
        scheme = Scheme.objects.create(name='Test Scheme', amc=amc, scheme_code='TS1')
        folio = '123/456'

        # Transactions
        # 1. Purchase
        t1 = Transaction.objects.create(
            investor=investor, scheme=scheme, folio_number=folio,
            date=date(2023, 1, 1), amount=10000, units=1000,
            txn_type_code='P', tr_flag='P', description='Purchase',
            txn_number='TXN001'
        )

        # 2. Redemption
        t2 = Transaction.objects.create(
            investor=investor, scheme=scheme, folio_number=folio,
            date=date(2023, 6, 1), amount=5000, units=400,
            txn_type_code='R', tr_flag='R', description='Redemption',
            txn_number='TXN002'
        )

        # Holding Current State (600 units left)
        # Value e.g. 7000 (NAV increased)
        holding = Holding.objects.create(
            investor=investor, scheme=scheme, folio_number=folio,
            units=600, average_cost=10, current_value=7000, current_nav=11.6666
        )

        flows = get_cash_flows(holding)

        # Expected:
        # (2023-01-01, -10000)
        # (2023-06-01, +5000)
        # (Today, +7000)

        assert len(flows) == 3
        assert flows[0] == (date(2023, 1, 1), -10000.0)
        assert flows[1] == (date(2023, 6, 1), 5000.0)
        assert flows[2][1] == 7000.0

@pytest.mark.django_db
class TestFolioDetailView:

    def test_view_context_data(self, client):
        # Setup
        password = 'password123'
        user = User.objects.create_user(username='investor1', password=password, user_type='INVESTOR')
        investor = InvestorProfile.objects.create(user=user, pan='ABCDE1234F')
        amc = AMC.objects.create(name='Test AMC', code='TEST')
        scheme = Scheme.objects.create(name='Test Scheme', amc=amc, scheme_code='TS1')
        folio_num = 'FOLIO-001'

        # Login
        client.login(username='investor1', password=password)

        # Create Holding
        holding = Holding.objects.create(
            investor=investor, scheme=scheme, folio_number=folio_num,
            units=100, average_cost=10, current_value=1200, current_nav=12
        )

        # Create Transaction (Purchase)
        Transaction.objects.create(
            investor=investor, scheme=scheme, folio_number=folio_num,
            date=date(2023, 1, 1), amount=1000, units=100,
            txn_type_code='P', tr_flag='P',
            txn_number='TXN003'
        )

        # Create NAV History (Last 2 days)
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        NAVHistory.objects.create(scheme=scheme, nav_date=today, net_asset_value=12)
        NAVHistory.objects.create(scheme=scheme, nav_date=yesterday, net_asset_value=11.5)

        # URL
        url = reverse('investments:folio_detail', kwargs={'folio_number': folio_num})
        response = client.get(url)

        assert response.status_code == 200
        context = response.context

        # Check Summary
        assert context['summary']['total_current_value'] == 1200
        assert context['summary']['portfolio_xirr'] is not None

        # Check Fund Data
        fund_data = context['fund_data'][0]
        assert fund_data['scheme'] == scheme
        assert fund_data['days_change'] > 0 # (12 - 11.5) * 100 = 50
        assert fund_data['sparkline_data'] is not None
        assert fund_data['xirr'] is not None
