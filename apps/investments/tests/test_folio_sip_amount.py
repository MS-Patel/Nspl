import pytest
from django.urls import reverse
from apps.users.factories import UserFactory, InvestorProfileFactory
from apps.products.factories import SchemeFactory
from apps.reconciliation.models import Holding, Transaction
from decimal import Decimal
import json

@pytest.mark.django_db
def test_folio_sip_amount_calculation(client):
    # Setup
    investor = InvestorProfileFactory()
    scheme = SchemeFactory()
    folio_number = 'SIPTEST123'

    # Create Holding (required for view to not 404)
    Holding.objects.create(
        investor=investor,
        scheme=scheme,
        folio_number=folio_number,
        units=100,
        average_cost=10,
        current_value=1200
    )

    # Create Transaction with Stamp Duty
    # SIP Amount = 1000. Amount (Invested) = 999.95. Stamp Duty = 0.05
    Transaction.objects.create(
        investor=investor,
        scheme=scheme,
        folio_number=folio_number,
        txn_number='TXN001',
        date='2024-01-01',
        amount=Decimal('999.95'),
        stamp_duty=Decimal('0.05'),
        units=10,
        txn_type_code='P',
        rta_code='CAMS',
        source='RTA'
    )

    client.force_login(investor.user)
    url = reverse('investments:folio_detail', kwargs={'folio_number': folio_number})

    response = client.get(url)
    assert response.status_code == 200

    # Verify Context
    fund_data = response.context['fund_data']
    assert len(fund_data) == 1
    transactions_json = fund_data[0]['transactions_json']

    txns = json.loads(transactions_json)
    assert len(txns) == 1
    txn = txns[0]

    # Check SIP Amount
    # 999.95 + 0.05 = 1000.0
    assert abs(txn['sip_amount'] - 1000.0) < 0.0001
    assert abs(txn['amount'] - 999.95) < 0.0001
