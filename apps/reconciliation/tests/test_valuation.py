from django.test import TestCase
from apps.users.models import User, InvestorProfile
from apps.products.models import Scheme, AMC, SchemeCategory, NAVHistory
from apps.reconciliation.models import Holding
from apps.reconciliation.utils.valuation import calculate_portfolio_valuation
from decimal import Decimal
from datetime import date

class ValuationTest(TestCase):
    def setUp(self):
        # User
        self.user = User.objects.create_user(username="INV001", email="test@example.com", user_type='INVESTOR')
        self.investor = InvestorProfile.objects.create(user=self.user, pan="ABCDE1234F")

        # Scheme
        self.amc = AMC.objects.create(name="HDFC", code="HDFC")
        self.category = SchemeCategory.objects.create(name="Equity")
        self.scheme = Scheme.objects.create(
            name="HDFC Top 100",
            scheme_code="HDFC100",
            amc=self.amc,
            category=self.category,
            isin="INF123"
        )

        # Holding (Cost 100, Units 10)
        self.holding = Holding.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            folio_number="12345/67",
            units=Decimal("10.0"),
            average_cost=Decimal("100.00")
        )

        # NAV History (Latest NAV 110)
        NAVHistory.objects.create(
            scheme=self.scheme,
            nav_date=date(2024, 1, 1),
            net_asset_value=Decimal("110.00")
        )

    def test_calculate_valuation(self):
        summary = calculate_portfolio_valuation(self.investor)

        # Verify Holdings Update
        self.holding.refresh_from_db()
        self.assertEqual(self.holding.current_nav, Decimal("110.00"))
        self.assertEqual(self.holding.current_value, Decimal("1100.00"))

        # Verify Summary
        self.assertEqual(summary['total_current_value'], Decimal("1100.00"))
        self.assertEqual(summary['total_invested_value'], Decimal("1000.00"))
        self.assertEqual(summary['total_gain_loss'], Decimal("100.00"))
