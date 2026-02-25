from django.test import TestCase
from django.urls import reverse, resolve
from apps.users import api_views

class APIConfigTest(TestCase):
    def test_rm_urls(self):
        url = reverse('users:api_rm_list_create')
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, api_views.RMListCreateAPIView)

        url = reverse('users:api_rm_detail', args=[1])
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, api_views.RMDetailAPIView)

    def test_distributor_urls(self):
        url = reverse('users:api_distributor_list_create')
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, api_views.DistributorListCreateAPIView)

        url = reverse('users:api_distributor_detail', args=[1])
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, api_views.DistributorDetailAPIView)
