from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.users.models import Branch, RMProfile
from apps.users.factories import UserFactory, RMProfileFactory
from django.db import connection, reset_queries

User = get_user_model()

class RMListPerformanceTest(TestCase):
    def setUp(self):
        # Create Admin User
        self.admin_user = UserFactory(username='admin', user_type=User.Types.ADMIN, is_staff=True, is_superuser=True)
        self.client.force_login(self.admin_user)

        # Create Branch
        self.branch = Branch.objects.create(
            name="Main Branch",
            code="MB001",
            city="Mumbai"
        )

        # Create 5 RMs
        self.rms = []
        for i in range(5):
            # RMProfileFactory creates a user automatically
            rm = RMProfileFactory(branch=self.branch)
            self.rms.append(rm)

    def test_rm_list_query_count(self):
        url = reverse('users:rm_list')

        # Clear any previous queries
        reset_queries()

        # Optimized query count:
        # 1. Session lookup
        # 2. User lookup (request.user)
        # 3. RM List with joined User and Branch (1 query)
        with self.assertNumQueries(3):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
