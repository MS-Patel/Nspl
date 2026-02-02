import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.users.factories import UserFactory, DistributorProfileFactory, RMProfileFactory

User = get_user_model()

@pytest.mark.django_db
class TestDistributorListPerformance:
    def test_distributor_list_query_count(self, client, django_assert_num_queries):
        # 1. Create Admin User
        admin_user = UserFactory(username='admin', user_type=User.Types.ADMIN, is_staff=True, is_superuser=True)
        client.force_login(admin_user)

        # 2. Create Distributors with RMs
        # Create 5 distributors
        # DistributorProfileFactory creates User and RMProfile (which creates User)
        distributors = []
        for _ in range(5):
             dist = DistributorProfileFactory()
             distributors.append(dist)

        url = reverse('users:distributor_list')

        # 3. Measure Queries
        # We expect a high number of queries due to N+1 problem.
        # 1. Session
        # 2. User (request.user)
        # 3. List Distributors (1 query)
        # 4. For each distributor (5 distributors):
        #    - Fetch dist.user (1 query)
        #    - Fetch dist.rm (1 query)
        #    - Fetch dist.rm.user (1 query)
        # Total = 2 + 1 + 5 * 3 = 18 queries (approx)

        # We set an expected value. If it fails, pytest will tell us the actual count.
        # Optimized query count:
        # 1. Session lookup
        # 2. User lookup (request.user)
        # 3. Distributor List with joined User and RM/RM.User
        with django_assert_num_queries(3):
             response = client.get(url)

        assert response.status_code == 200
