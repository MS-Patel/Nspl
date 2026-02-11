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

    def test_valuation_performance(self):
        """
        Ensure valuation does not suffer from N+1 query problem.
        """
        # Create multiple schemes and holdings
        num_holdings = 50
        schemes = [
            Scheme(
                amc=self.amc,
                category=self.category,
                name=f"Perf Scheme {i}",
                scheme_code=f"PSC{i}",
                isin=f"PISIN{i}"
            )
            for i in range(num_holdings)
        ]
        Scheme.objects.bulk_create(schemes)
        created_schemes = list(Scheme.objects.filter(scheme_code__startswith="PSC"))

        holdings = [
            Holding(
                investor=self.investor,
                scheme=scheme,
                folio_number=f"PF{i}",
                units=Decimal("10.0"),
                average_cost=Decimal("100.00")
            )
            for i, scheme in enumerate(created_schemes)
        ]
        Holding.objects.bulk_create(holdings)

        nav_entries = [
            NAVHistory(
                scheme=scheme,
                nav_date=date(2024, 1, 1),
                net_asset_value=Decimal("100.00")
            )
            for scheme in created_schemes
        ]
        NAVHistory.objects.bulk_create(nav_entries)

        # Clear any cached lookups
        self.investor.refresh_from_db()

        # Expected queries:
        # 1. Select Holdings with Subquery for NAV
        # 2. Bulk Update Holdings
        with self.assertNumQueries(2):
            calculate_portfolio_valuation(self.investor)

    def test_calculate_valuation_rounding(self):
        """
        Verify that total valuation figures are rounded to 2 decimal places.
        Scenario:
        Units: 10.1234
        NAV: 123.4567
        Current Value (Raw): 1249.79607778
        Rounded Value: 1249.80
        """
        # Update existing holding with high precision values
        self.holding.units = Decimal("10.1234")
        self.holding.average_cost = Decimal("100.1234")
        self.holding.save()

        # Update NAV history with high precision
        nav = NAVHistory.objects.get(scheme=self.scheme)
        nav.net_asset_value = Decimal("123.4567")
        nav.save()

        summary = calculate_portfolio_valuation(self.investor)

        # Expected Calculation:
        # Invested: 10.1234 * 100.1234 = 1013.58920356 -> Rounded: 1013.59
        # Current: 10.1234 * 123.4567 = 1249.79607778 -> Rounded: 1249.80
        # Gain: 1249.79607778 - 1013.58920356 = 236.20687422 -> Rounded: 236.21

        self.assertEqual(summary['total_invested_value'], Decimal("1013.59"))
        self.assertEqual(summary['total_current_value'], Decimal("1249.80"))

        # Note: Depending on how gain is calculated (A-B or sum of gains)
        # In code: round(total_current - total_invested, 2)
        # Unrounded Diff: 236.20687422 -> Rounded: 236.21
        self.assertEqual(summary['total_gain_loss'], Decimal("236.21"))
