import pytest
from django.urls import reverse
from django.conf import settings
from django.test import override_settings
from django.db import connection, reset_queries
from apps.investments.factories import OrderFactory
from apps.users.factories import UserFactory
from apps.investments.models import Order

@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_order_list_performance_optimized(client):
    """
    Test to verify that order_list view is optimized and does not suffer from N+1 queries.
    """
    # Create an admin user
    user = UserFactory(user_type='ADMIN')
    client.force_login(user)

    # --- Scenario 1: 5 Orders ---
    OrderFactory.create_batch(5)

    reset_queries()
    client.get(reverse('investments:order_list'))
    query_count_5 = len(connection.queries)
    print(f"\nQueries with 5 orders: {query_count_5}")

    # --- Scenario 2: 10 Orders ---
    # We clear existing orders to isolate the count purely on N
    Order.objects.all().delete()
    OrderFactory.create_batch(10)

    reset_queries()
    client.get(reverse('investments:order_list'))
    query_count_10 = len(connection.queries)
    print(f"Queries with 10 orders: {query_count_10}")

    # Check for Optimization
    # The count should be constant (O(1)) regardless of the number of orders.
    # We allow a small margin of error (e.g., +2) just in case, but ideally it should be equal.

    assert query_count_10 <= query_count_5 + 2, \
        f"Query count grew from {query_count_5} to {query_count_10}, suggesting N+1 issue persists."
