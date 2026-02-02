import pytest
from django.urls import reverse
from django.db import connection, reset_queries
from apps.users.factories import UserFactory, InvestorProfileFactory, DistributorProfileFactory
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_investor_list_query_count_repro(client, settings):
    settings.DEBUG = True

    # Create Admin User
    admin_user = UserFactory(username='admin', user_type=User.Types.ADMIN, is_staff=True, is_superuser=True)
    client.force_login(admin_user)

    # Create 5 Investors, each with a Distributor
    # This setup ensures we trigger the N+1:
    # 1. Fetch Investor
    # 2. Access Investor.User
    # 3. Access Investor.Distributor
    # 4. Access Investor.Distributor.User
    for i in range(5):
        dist = DistributorProfileFactory()
        InvestorProfileFactory(distributor=dist)

    url = reverse('users:investor_list')

    # Run the request and count queries
    reset_queries()
    response = client.get(url)

    query_count = len(connection.queries)
    print(f"\nQuery count: {query_count}")

    # We expect optimized behavior.
    # Base: 2 (Session + User)
    # List: 1 (with all joins)
    # Total roughly: 3.

    assert query_count <= 5, f"Expected <= 5 queries (Optimized), got {query_count}"
    assert response.status_code == 200
