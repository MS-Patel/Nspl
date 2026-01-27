import pytest
from unittest.mock import patch
from apps.investments.models import Order
from apps.investments.factories import OrderFactory
from apps.integration.sync_utils import sync_pending_orders

@pytest.mark.django_db
def test_sync_pending_orders_does_not_reject_on_api_error():
    """
    Test that an API error (e.g. Connection rejected) does NOT
    mark the order as REJECTED locally. It should remain in its original state.
    """
    # 1. Setup: Create an order in SENT_TO_BSE state
    order = OrderFactory(
        status=Order.SENT_TO_BSE,
        bse_order_id="12345",
        bse_remarks="Sent to BSE"
    )

    # 2. Mock BSEStarMFClient
    with patch('apps.integration.sync_utils.BSEStarMFClient') as MockClientClass:
        mock_client = MockClientClass.return_value

        # Simulate API Error containing "rejected" (e.g., Connection rejected)
        mock_client.get_payment_status.return_value = {
            'status': 'error',
            'remarks': 'Connection rejected by peer'
        }

        # Mock get_order_status to return None (simulating failure or no update)
        mock_client.get_order_status.return_value = None

        # 3. Call Sync
        sync_pending_orders(investor=order.investor)

        # 4. Assert
        order.refresh_from_db()

        # Expectation: Status should NOT change to REJECTED. It should remain SENT_TO_BSE.
        assert order.status == Order.SENT_TO_BSE
        assert order.status != Order.REJECTED
