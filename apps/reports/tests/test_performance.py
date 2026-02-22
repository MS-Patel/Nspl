from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.db import connection, reset_queries
from apps.users.models import User, InvestorProfile, BankAccount, Nominee
from apps.reports.views import InvestorReportView

class InvestorReportPerformanceTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='investor', password='password', user_type=User.Types.INVESTOR)

        self.admin = User.objects.create_superuser(username='admin', password='password', user_type=User.Types.ADMIN)
        self.client.force_login(self.admin)

        # Create N investors
        self.num_investors = 10
        for i in range(self.num_investors):
            u = User.objects.create(username=f'inv{i}', user_type=User.Types.INVESTOR)
            inv = InvestorProfile.objects.create(user=u, pan=f'PAN{i}')
            BankAccount.objects.create(investor=inv, account_number=f'123{i}', ifsc_code='IFSC', is_default=True)
            Nominee.objects.create(investor=inv, name=f'Nom{i}', relationship='Spouse', percentage=100)

    def test_investor_report_queries(self):
        # Admin sees all investors
        self.client.force_login(self.admin)

        reset_queries()
        # Expected queries:
        # 1. Session
        # 2. User
        # 3. InvestorProfile (Main)
        # 4. BankAccount (Prefetch)
        # 5. Nominee (Prefetch)
        # Total = 5
        with self.assertNumQueries(5):
            response = self.client.get(reverse('reports:investor_report'))

        self.assertEqual(response.status_code, 200)
