import pytest
from unittest.mock import patch
from django.urls import reverse
from apps.investments.models import Order
from apps.investments.factories import OrderFactory
from apps.users.factories import InvestorProfileFactory
from apps.products.factories import SchemeFactory

@pytest.mark.django_db
def test_order_submission_rejection_on_connection_error(client):
    """
    Test that an order submission fails gracefully without marking the order as REJECTED
    when a connection error occurs during the BSE API call.
    Currently reproduces the bug where it IS marked REJECTED.
    """
    # 1. Setup User and Login
    # Correctly create an InvestorProfile, which creates the linked User
    investor = InvestorProfileFactory()
    user = investor.user
    client.force_login(user)

    scheme = SchemeFactory()

    # 2. Mock BSEStarMFClient.place_order to simulate Connection Error
    with patch('apps.integration.bse_client.BSEStarMFClient.place_order') as mock_place_order:
        # Simulate an exception being caught and returned as 'exception' (which is what we changed code to do)
        mock_place_order.return_value = {
            'status': 'exception',
            'remarks': 'Connection rejected by peer'
        }

        # 3. Submit Order Form
        url = reverse('investments:order_create')
        data = {
            'investor': investor.id, # Investor field was missing in previous attempt
            'scheme': scheme.id,
            'transaction_type': Order.PURCHASE,
            'amount': 5000,
            'payment_mode': Order.DIRECT
        }

        response = client.post(url, data)

        if response.status_code == 200:
             # Form invalid?
             print(response.context['form'].errors)

        # 4. Assert Redirect (Success flow redirects to list)
        assert response.status_code == 302
        assert response.url == reverse('investments:order_list')

        # 5. Verify Order Status
        # Find the created order
        order = Order.objects.filter(investor=investor).last()
        assert order is not None

        # We assert the DESIRED behavior (PENDING), which should FAIL now because current code rejects it.
        assert order.status == Order.PENDING, \
            f"Order status should be PENDING on connection error, but was {order.status}. Remarks: {order.bse_remarks}"
