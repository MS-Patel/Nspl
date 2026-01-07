from django.test import TestCase
from apps.products.models import AMC, Scheme, SchemeCategory
from django.core.management import call_command
from django.urls import reverse
from django.contrib.auth import get_user_model
import json

class SchemeModelTest(TestCase):
    def test_scheme_creation(self):
        amc = AMC.objects.create(name="Test AMC", code="TEST_AMC")
        scheme = Scheme.objects.create(
            amc=amc,
            name="Test Scheme",
            isin="INF123456789",
            scheme_code="TEST001",
            scheme_type="EQUITY",
            min_purchase_amount=5000
        )
        self.assertEqual(scheme.name, "Test Scheme")
        self.assertEqual(scheme.amc.code, "TEST_AMC")

class ImportCommandTest(TestCase):
    def test_import_command(self):
        # We rely on the sample file created in the previous steps
        # This test ensures the command runs without error and populates the DB
        call_command('import_schemes')
        self.assertTrue(Scheme.objects.count() > 0)
        self.assertTrue(AMC.objects.count() > 0)

class SchemeViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='password'
        )
        self.client.login(username='testuser', password='password')

        amc = AMC.objects.create(name="Test AMC", code="TEST_AMC")
        category = SchemeCategory.objects.create(name="Equity", code="EQUITY")
        Scheme.objects.create(
            amc=amc,
            category=category,
            name="Test Scheme 1",
            isin="INF001",
            scheme_code="S001",
            min_purchase_amount=1000
        )

    def test_scheme_list_view(self):
        response = self.client.get(reverse('scheme_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('grid_data_json', response.context)

        data = json.loads(response.context['grid_data_json'])
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], "Test Scheme 1")
