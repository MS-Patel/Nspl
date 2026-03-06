import pytest
from decimal import Decimal
from django.utils import timezone
from django.core.management import call_command
from apps.users.factories import InvestorProfileFactory, DistributorProfileFactory
from apps.products.factories import SchemeFactory, NAVHistoryFactory
from apps.reconciliation.models import Holding, Transaction
from apps.reconciliation.utils.reconcile import recalculate_holding
from apps.payouts.models import Payout
from apps.payouts.utils import calculate_payouts

# Mock Factories need to be assumed or created if missing.
# Since I cannot see factories.py fully, I will use standard Django object creation for reliability.

@pytest.mark.django_db
class TestHoldingValuationUpdate:
    def test_update_holding_values_command(self):
        # 1. Setup
        scheme = SchemeFactory(name="Test Scheme")
        investor = InvestorProfileFactory()

        # Create Holding with old value
        holding = Holding.objects.create(
            investor=investor,
            scheme=scheme,
            folio_number="12345",
            units=Decimal("100.00"),
            average_cost=Decimal("10.00"),
            current_nav=Decimal("10.00"),
            current_value=Decimal("1000.00"),
            last_updated=timezone.now() - timezone.timedelta(days=5)
        )

        # Create NEW NAV History
        NAVHistoryFactory(
            scheme=scheme,
            nav_date=timezone.now().date(),
            net_asset_value=Decimal("15.00")
        )

        # 2. Execute Command
        call_command('update_holding_values')

        # 3. Verify
        holding.refresh_from_db()
        assert holding.current_nav == Decimal("15.00")
        assert holding.current_value == Decimal("1500.00") # 100 * 15
        assert holding.last_updated.date() == timezone.now().date()

@pytest.mark.django_db
class TestRecalculateHoldingExtended:
    def test_recalculate_with_dividend_reinvestment(self):
        scheme = SchemeFactory()
        investor = InvestorProfileFactory()
        folio = "DIV123"

        # Purchase
        Transaction.objects.create(
            investor=investor, scheme=scheme, folio_number=folio,
            txn_type_code="P", txn_number="TXN1", date=timezone.now().date(),
            amount=Decimal("1000"), units=Decimal("100"), rta_code="CAMS"
        )

        # Dividend Reinvestment (DR)
        # Units increase, Amount is reinvested (so treated as purchase cost wise?)
        # Logic says: total_cost = (units * wac) + amount.
        # WAC = 10.
        # DR: Amt 100, Units 10. (NAV 10).
        # New Cost = (100*10) + 100 = 1100. New Units = 110. WAC = 10. Correct.
        Transaction.objects.create(
            investor=investor, scheme=scheme, folio_number=folio,
            txn_type_code="DR", txn_number="TXN2", date=timezone.now().date(),
            amount=Decimal("100"), units=Decimal("10"), rta_code="CAMS"
        )

        recalculate_holding(investor, scheme, folio)

        h = Holding.objects.get(folio_number=folio)
        assert h.units == Decimal("110")
        assert h.average_cost == Decimal("10") # Should stay same if reinvested at same NAV approx

    def test_recalculate_with_bonus(self):
        scheme = SchemeFactory()
        investor = InvestorProfileFactory()
        folio = "BON123"

        # Purchase: 100 units @ 10 = 1000
        Transaction.objects.create(
            investor=investor, scheme=scheme, folio_number=folio,
            txn_type_code="P", txn_number="TXN1", date=timezone.now().date(),
            amount=Decimal("1000"), units=Decimal("100"), rta_code="CAMS"
        )

        # Bonus: 1:1 -> 100 units free.
        Transaction.objects.create(
            investor=investor, scheme=scheme, folio_number=folio,
            txn_type_code="B", txn_number="TXN2", date=timezone.now().date(),
            amount=Decimal("0"), units=Decimal("100"), rta_code="CAMS"
        )

        recalculate_holding(investor, scheme, folio)

        h = Holding.objects.get(folio_number=folio)
        assert h.units == Decimal("200")
        # Cost Basis: Total Cost (1000) / Total Units (200) = 5.
        assert h.average_cost == Decimal("5.00")

    def test_recalculate_with_reversal(self):
        scheme = SchemeFactory()
        investor = InvestorProfileFactory()
        folio = "REV123"

        # Purchase: 100 units @ 10
        Transaction.objects.create(
            investor=investor, scheme=scheme, folio_number=folio,
            txn_type_code="P", txn_number="TXN1", date=timezone.now().date(),
            amount=Decimal("1000"), units=Decimal("100"), rta_code="CAMS"
        )

        # Reversal (J): -10 units
        # J now correctly mapped to no effect. Let's make it an actual ADD with negative units (like a Purchase Rejection).
        Transaction.objects.create(
            investor=investor, scheme=scheme, folio_number=folio,
            txn_type_code="ADDR", txn_number="TXN2", date=timezone.now().date(),
            amount=Decimal("-100"), units=Decimal("-10"), rta_code="CAMS",
            txn_action="ADD"
        )

        recalculate_holding(investor, scheme, folio)

        h = Holding.objects.get(folio_number=folio)
        assert h.units == Decimal("90")
        assert h.average_cost == Decimal("10.00")

    def test_regression_redemption_matches_p(self):
        """
        Regression Test: Ensure 'REDEMPTION' is not treated as 'PURCHASE'
        because it contains the letter 'P'.
        """
        scheme = SchemeFactory()
        investor = InvestorProfileFactory()
        folio = "REG123"

        # Purchase: 100 units @ 10
        Transaction.objects.create(
            investor=investor, scheme=scheme, folio_number=folio,
            txn_type_code="P", txn_number="TXN1", date=timezone.now().date(),
            amount=Decimal("1000"), units=Decimal("100"), rta_code="CAMS"
        )

        # Redemption: 10 units (Stored as positive in DB but type is REDEMPTION)
        Transaction.objects.create(
            investor=investor, scheme=scheme, folio_number=folio,
            txn_type_code="R", txn_number="TXN2", date=timezone.now().date(),
            amount=Decimal("100"), units=Decimal("10"), rta_code="CAMS",
            txn_action="SUB"
        )

        recalculate_holding(investor, scheme, folio)

        h = Holding.objects.get(folio_number=folio)
        # Should be 90 (100 - 10). If regression exists, it would be 110.
        assert h.units == Decimal("90")
