from django.test import TestCase, Client
from django.urls import reverse
from apps.users.models import User

class MandateReportViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(username='admin', password='password', user_type=User.Types.ADMIN)
        self.client.force_login(self.admin_user)

    def test_mandate_report_view_status(self):
        response = self.client.get(reverse('reports:mandate_report'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/mandate_report.html')
        self.assertIn('grid_data_json', response.context)
