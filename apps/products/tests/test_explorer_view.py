from django.test import TestCase, Client
from django.urls import reverse
from apps.products.models import Scheme, AMC, SchemeCategory
from apps.products.factories import SchemeFactory, AMCFactory, SchemeCategoryFactory
from apps.users.factories import UserFactory

class SchemeExplorerViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('products:scheme_explore')

        # Create User and Login
        self.user = UserFactory(username='testuser', password='password')
        self.client.force_login(self.user)

        # Create Categories
        self.cat_equity = SchemeCategoryFactory(name='Equity', code='EQ')
        self.cat_debt = SchemeCategoryFactory(name='Debt', code='DEBT')
        self.cat_hybrid = SchemeCategoryFactory(name='Hybrid', code='HYB')

        # Create AMCs
        self.amc_hdfc = AMCFactory(name='HDFC Mutual Fund', code='HDFC')
        self.amc_sbi = AMCFactory(name='SBI Mutual Fund', code='SBI')

        # Create Schemes
        self.scheme1 = SchemeFactory(
            name='HDFC Equity Fund',
            category=self.cat_equity,
            amc=self.amc_hdfc,
            scheme_type='Open Ended',
            riskometer='High'
        )
        self.scheme2 = SchemeFactory(
            name='SBI Debt Fund',
            category=self.cat_debt,
            amc=self.amc_sbi,
            scheme_type='Open Ended',
            riskometer='Low'
        )
        self.scheme3 = SchemeFactory(
            name='HDFC Hybrid Fund',
            category=self.cat_hybrid,
            amc=self.amc_hdfc,
            scheme_type='Close Ended',
            riskometer='Moderate'
        )

    def test_view_status_code(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_filter_single_category(self):
        response = self.client.get(self.url, {'category': self.cat_equity.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'HDFC Equity Fund')
        self.assertNotContains(response, 'SBI Debt Fund')
        self.assertNotContains(response, 'HDFC Hybrid Fund')

    def test_filter_multiple_categories(self):
        # Simulate multiple selections for the same key 'category'
        # Client.get handles list values for query parameters correctly
        response = self.client.get(self.url, {'category': [self.cat_equity.id, self.cat_debt.id]})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'HDFC Equity Fund')
        self.assertContains(response, 'SBI Debt Fund')
        self.assertNotContains(response, 'HDFC Hybrid Fund')

    def test_filter_multiple_amcs(self):
        response = self.client.get(self.url, {'amc': [self.amc_hdfc.id, self.amc_sbi.id]})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'HDFC Equity Fund')
        self.assertContains(response, 'SBI Debt Fund')
        self.assertContains(response, 'HDFC Hybrid Fund')

    def test_filter_combined(self):
        # Filter for HDFC schemes that are Equity
        response = self.client.get(self.url, {
            'amc': [self.amc_hdfc.id],
            'category': [self.cat_equity.id]
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'HDFC Equity Fund')
        self.assertNotContains(response, 'SBI Debt Fund')
        self.assertNotContains(response, 'HDFC Hybrid Fund')

    def test_filter_riskometer(self):
        response = self.client.get(self.url, {'risk': ['High', 'Low']})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'HDFC Equity Fund')
        self.assertContains(response, 'SBI Debt Fund')
        self.assertNotContains(response, 'HDFC Hybrid Fund')

    def test_context_preservation(self):
        # Ensure selected filters are passed back to context
        response = self.client.get(self.url, {'category': [self.cat_equity.id, self.cat_debt.id]})
        self.assertEqual(response.status_code, 200)
        self.assertIn('selected_categories', response.context)
        # Verify the list contains the expected items (order might vary)
        self.assertEqual(set(response.context['selected_categories']), {self.cat_equity.id, self.cat_debt.id})
