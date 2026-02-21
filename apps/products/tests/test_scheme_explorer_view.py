from django.test import TestCase
from django.urls import reverse
from apps.products.factories import SchemeFactory
from apps.users.factories import UserFactory
from apps.products.models import Scheme

class SchemeExplorerViewTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_login(self.user)
        # Use 'products:scheme_explore' based on urls.py
        self.url = reverse('products:scheme_explore')

    def test_sort_popularity_descending_aum(self):
        # Create schemes with different AUM
        s1 = SchemeFactory(name="Scheme A", aum=100.00)
        s2 = SchemeFactory(name="Scheme B", aum=500.00)
        s3 = SchemeFactory(name="Scheme C", aum=50.00)

        response = self.client.get(self.url, {'sort': 'popularity'})
        self.assertEqual(response.status_code, 200)

        # Schemes in context are paginated, so we get page_obj or object_list
        schemes = list(response.context['schemes'])

        # Expected: B (500), A (100), C (50)
        self.assertEqual(schemes[0].id, s2.id)
        self.assertEqual(schemes[1].id, s1.id)
        self.assertEqual(schemes[2].id, s3.id)

    def test_sort_rating_high_to_low(self):
        # High Risk First (High -> Low)
        # 'Very High' -> 6, 'High' -> 5, 'Low' -> 1
        s1 = SchemeFactory(name="Scheme Low", riskometer='Low')
        s2 = SchemeFactory(name="Scheme High", riskometer='High')
        s3 = SchemeFactory(name="Scheme Very High", riskometer='Very High')

        response = self.client.get(self.url, {'sort': 'rating_high'})
        self.assertEqual(response.status_code, 200)

        schemes = list(response.context['schemes'])

        # Expected: Very High, High, Low
        self.assertEqual(schemes[0].id, s3.id)
        self.assertEqual(schemes[1].id, s2.id)
        self.assertEqual(schemes[2].id, s1.id)

    def test_sort_rating_low_to_high(self):
        # Low Risk First (Low -> High)
        # 'Low' -> 1, 'Moderate' -> 3, 'High' -> 5
        s1 = SchemeFactory(name="Scheme Low", riskometer='Low')
        s2 = SchemeFactory(name="Scheme Mod", riskometer='Moderate')
        s3 = SchemeFactory(name="Scheme High", riskometer='High')

        response = self.client.get(self.url, {'sort': 'rating_low'})
        self.assertEqual(response.status_code, 200)

        schemes = list(response.context['schemes'])

        # Expected: Low, Moderate, High
        self.assertEqual(schemes[0].id, s1.id)
        self.assertEqual(schemes[1].id, s2.id)
        self.assertEqual(schemes[2].id, s3.id)

    def test_ajax_request_returns_partial(self):
        SchemeFactory()
        # Simulate AJAX request
        response = self.client.get(
            self.url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/partials/scheme_list_partial.html')
        self.assertTemplateNotUsed(response, 'products/scheme_explore.html')
