from django.test import TestCase, Client
from django.urls import reverse

class WebsiteTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_page(self):
        response = self.client.get(reverse('website:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "BEFORE YOU SPEND")

    def test_about_page(self):
        response = self.client.get(reverse('website:about'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "About Us")

    def test_contact_page(self):
        response = self.client.get(reverse('website:contact'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contact Us")

    def test_mutual_funds_page(self):
        response = self.client.get(reverse('website:mutual_funds'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mutual Funds")
