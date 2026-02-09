from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.payouts.models import BrokerageImport
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

class TestBrokerageUploadView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin', password='password', user_type=User.Types.ADMIN)
        self.client.force_login(self.user)
        self.url = reverse('payouts:upload')

    def test_duplicate_check_returns_409(self):
        BrokerageImport.objects.create(month=1, year=2024)
        response = self.client.post(self.url, {
            'month': 1,
            'year': 2024,
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['status'], 'conflict')

    def test_overwrite_deletes_old_and_proceeds(self):
        old_import = BrokerageImport.objects.create(month=1, year=2024)
        old_id = old_import.id

        response = self.client.post(self.url, {
            'month': 1,
            'year': 2024,
            'overwrite': 'true'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertFalse(BrokerageImport.objects.filter(id=old_id).exists())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertTrue(BrokerageImport.objects.filter(month=1, year=2024).exists())

    def test_overwrite_safe_rollback_on_invalid_file(self):
        # Setup existing
        old_import = BrokerageImport.objects.create(month=2, year=2024)
        old_id = old_import.id

        # Invalid file (txt extension)
        invalid_file = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")

        response = self.client.post(self.url, {
            'month': 2,
            'year': 2024,
            'overwrite': 'true',
            'cams_file': invalid_file
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        # Should fail validation (400)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')

        # Verify OLD object still exists (Rollback worked)
        self.assertTrue(BrokerageImport.objects.filter(id=old_id).exists())
