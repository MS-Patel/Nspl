from django.test import TestCase
from django.urls import reverse
from apps.users.models import User
from apps.products.factories import SchemeFactory, AMCFactory, SchemeCategoryFactory
from apps.products.models import Scheme

class SchemeExplorerViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='password', user_type=User.Types.ADMIN
        )
        self.client.force_login(self.user)

        self.amc = AMCFactory(name="Test AMC")
        self.category = SchemeCategoryFactory(name="Equity")
        self.scheme1 = SchemeFactory(name="Alpha Fund", amc=self.amc, category=self.category, riskometer='High')
        self.scheme2 = SchemeFactory(name="Beta Fund", amc=self.amc, category=self.category, riskometer='Low')

    def test_explorer_view_status_code(self):
        url = reverse('products:scheme_explore')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_explorer_view_context(self):
        url = reverse('products:scheme_explore')
        response = self.client.get(url)
        self.assertTrue('schemes' in response.context)
        # Assuming no other schemes in DB, length should be 2.
        # But to be safe, check if our schemes are present.
        scheme_ids = [s.id for s in response.context['schemes']]
        self.assertIn(self.scheme1.id, scheme_ids)
        self.assertIn(self.scheme2.id, scheme_ids)

        self.assertTrue('amcs' in response.context)
        self.assertTrue('categories' in response.context)
        self.assertTrue('risks' in response.context)

    def test_search_filter(self):
        url = reverse('products:scheme_explore')
        response = self.client.get(url, {'search': 'Alpha'})
        self.assertEqual(len(response.context['schemes']), 1)
        self.assertEqual(response.context['schemes'][0].name, "Alpha Fund")

    def test_risk_filter(self):
        url = reverse('products:scheme_explore')
        response = self.client.get(url, {'risk': 'High'})
        self.assertEqual(len(response.context['schemes']), 1)
        self.assertEqual(response.context['schemes'][0].name, "Alpha Fund")
