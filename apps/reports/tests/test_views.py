from django.test import TestCase, Client
from django.urls import reverse
from apps.users.models import User

class ReportViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(username='admin', password='password', user_type=User.Types.ADMIN)
        self.client.force_login(self.admin_user)

    def test_dashboard_view(self):
        response = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_investor_report_view(self):
        response = self.client.get(reverse('reports:investor_report'))
        self.assertEqual(response.status_code, 200)

    def test_transaction_report_view(self):
        response = self.client.get(reverse('reports:transaction_report'))
        self.assertEqual(response.status_code, 200)

    def test_master_report_view_distributor(self):
        response = self.client.get(reverse('reports:master_report', kwargs={'type': 'distributor'}))
        self.assertEqual(response.status_code, 200)

    def test_master_report_view_scheme(self):
        response = self.client.get(reverse('reports:master_report', kwargs={'type': 'scheme'}))
        self.assertEqual(response.status_code, 200)
