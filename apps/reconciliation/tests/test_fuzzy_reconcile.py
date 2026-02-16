import pytest
from decimal import Decimal
from django.utils import timezone
from apps.reconciliation.models import Transaction, Holding
from apps.reconciliation.utils.reconcile import recalculate_holding
from apps.users.models import InvestorProfile, User
from apps.products.models import Scheme, AMC

@pytest.mark.django_db
def test_recalculate_holding_reversal_logic():
    # Setup
    user = User.objects.create_user(username='TESTUSER', password='password')
    investor = InvestorProfile.objects.create(user=user, pan='ABCDE1234F')
    amc = AMC.objects.create(name='Test AMC', code='TEST')
    scheme = Scheme.objects.create(amc=amc, scheme_code='TESTSCHEME', name='Test Scheme')
    folio = '1234567890'

    # 1. Initial Purchase (Standard Code 'P')
    Transaction.objects.create(
        investor=investor, scheme=scheme, folio_number=folio,
        txn_number='TXN001', date=timezone.now().date(),
        amount=10000, units=1000, txn_type_code='P', tr_flag='P', description='PURCHASE'
    )

    recalculate_holding(investor, scheme, folio)
    holding = Holding.objects.get(investor=investor, scheme=scheme, folio_number=folio)
    assert holding.units == 1000

    # 2. Add New Karvy Purchase Code ('SIN' - Systematic Investment)
    Transaction.objects.create(
        investor=investor, scheme=scheme, folio_number=folio,
        txn_number='TXN002', date=timezone.now().date(),
        amount=5000, units=500, txn_type_code='SIN', tr_flag='', description='Systematic Investment'
    )

    recalculate_holding(investor, scheme, folio)
    holding.refresh_from_db()
    assert holding.units == 1500 # 1000 + 500

    # 3. Add New CAMS Redemption Code ('R1' - Partial Redemption)
    Transaction.objects.create(
        investor=investor, scheme=scheme, folio_number=folio,
        txn_number='TXN003', date=timezone.now().date(),
        amount=2000, units=200, txn_type_code='R1', tr_flag='', description='Partial Redemption'
    )

    recalculate_holding(investor, scheme, folio)
    holding.refresh_from_db()
    assert holding.units == 1300 # 1500 - 200

    # 4. Test Purchase Reversal (Code 'SINR' - SIP Rejection)
    # This should reverse a purchase (reduce units)
    Transaction.objects.create(
        investor=investor, scheme=scheme, folio_number=folio,
        txn_number='TXN004', date=timezone.now().date(),
        amount=5000, units=500, txn_type_code='SINR', tr_flag='', description='SIP Rejection'
    )

    recalculate_holding(investor, scheme, folio)
    holding.refresh_from_db()
    assert holding.units == 800 # 1300 - 500 (Reversed the SIN)

    # 5. Test Redemption Reversal (Code 'REDR' - Redemption Rejection)
    # This should reverse a redemption (add units back)
    # Let's say we had a redemption of 200 earlier (TXN003). Now we reverse it.
    Transaction.objects.create(
        investor=investor, scheme=scheme, folio_number=folio,
        txn_number='TXN005', date=timezone.now().date(),
        amount=2000, units=200, txn_type_code='REDR', tr_flag='', description='Redemption Rejection'
    )

    recalculate_holding(investor, scheme, folio)
    holding.refresh_from_db()
    assert holding.units == 1000 # 800 + 200 (Reversed the R1)

    # 6. Test Fuzzy Logic Fallback (Unknown Code 'XYZ' but Description 'Purchase')
    Transaction.objects.create(
        investor=investor, scheme=scheme, folio_number=folio,
        txn_number='TXN006', date=timezone.now().date(),
        amount=1000, units=100, txn_type_code='XYZ', tr_flag='', description='Additional Purchase Systematic'
    )

    recalculate_holding(investor, scheme, folio)
    holding.refresh_from_db()
    assert holding.units == 1100 # 1000 + 100

    # 7. Test Flag Fallback (Unknown Code 'ABC' but Flag 'P')
    Transaction.objects.create(
        investor=investor, scheme=scheme, folio_number=folio,
        txn_number='TXN007', date=timezone.now().date(),
        amount=500, units=50, txn_type_code='ABC', tr_flag='P', description='Unknown'
    )

    recalculate_holding(investor, scheme, folio)
    holding.refresh_from_db()
    assert holding.units == 1150 # 1100 + 50

    # 8. Test Generic Reversal (J/REV) for Redemption
    # Assuming code 'REV' and description 'Redemption Reversal'
    Transaction.objects.create(
        investor=investor, scheme=scheme, folio_number=folio,
        txn_number='TXN008', date=timezone.now().date(),
        amount=1000, units=100, txn_type_code='REV', tr_flag='', description='Redemption Reversal'
    )
    recalculate_holding(investor, scheme, folio)
    holding.refresh_from_db()
    assert holding.units == 1250 # 1150 + 100

    print("\nAll Test Cases Passed Successfully!")

if __name__ == "__main__":
    # If run directly (not via pytest), minimal setup needed
    pass
