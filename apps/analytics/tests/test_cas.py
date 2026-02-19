import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.analytics.models import CASUpload, ExternalHolding
from apps.analytics.services.cas_parser import CASParser
from apps.users.factories import InvestorProfileFactory, UserFactory

@pytest.mark.django_db
class TestCASUpload:
    def test_cas_upload_model_creation(self):
        investor = InvestorProfileFactory()
        user = UserFactory()

        cas = CASUpload.objects.create(
            investor=investor,
            uploaded_by=user,
            file=SimpleUploadedFile("test.pdf", b"dummy content"),
            status=CASUpload.STATUS_PENDING
        )

        assert cas.status == "PENDING"
        assert cas.investor == investor
        assert cas.uploaded_by == user

    def test_external_holding_model_creation(self):
        investor = InvestorProfileFactory()
        cas = CASUpload.objects.create(
            investor=investor,
            file=SimpleUploadedFile("test.pdf", b"dummy content")
        )

        holding = ExternalHolding.objects.create(
            cas_upload=cas,
            investor=investor,
            scheme_name="Test Scheme",
            units=100.00,
            current_value=5000.00
        )

        assert holding.scheme_name == "Test Scheme"
        assert holding.units == 100.00
        assert holding.cas_upload == cas

    def test_parser_initialization(self):
        # We can't easily test full parsing without a real PDF,
        # but we can test the class structure and basic methods.
        parser = CASParser("dummy_path.pdf", password="password")
        assert parser.file_path == "dummy_path.pdf"
        assert parser.password == "password"

from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from apps.users.models import User, InvestorProfile
from apps.analytics.services.tasks import process_cas_upload
from decimal import Decimal

class CASUploadViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password', user_type=User.Types.INVESTOR)
        self.investor = InvestorProfile.objects.create(user=self.user, pan='ABCDE1234F', firstname='Test', email='test@example.com')
        self.client.login(username='testuser', password='password')
        self.url = reverse('analytics:cas_upload')

    @patch('apps.analytics.views.process_cas_upload')
    def test_cas_upload_starts_background_task(self, mock_process):
        # Create a dummy file
        from django.core.files.uploadedfile import SimpleUploadedFile
        file = SimpleUploadedFile("test.pdf", b"dummy content", content_type="application/pdf")

        response = self.client.post(self.url, {
            'file': file,
            'password': 'password'
        }, follow=True)

        self.assertRedirects(response, reverse('analytics:cas_list'))

        # Verify CASUpload created
        cas_upload = CASUpload.objects.first()
        self.assertIsNotNone(cas_upload)
        self.assertEqual(cas_upload.status, CASUpload.STATUS_PENDING)

    @patch('apps.analytics.views.threading.Thread')
    def test_cas_upload_threading(self, mock_thread_cls):
        from django.core.files.uploadedfile import SimpleUploadedFile
        file = SimpleUploadedFile("test.pdf", b"dummy content", content_type="application/pdf")

        response = self.client.post(self.url, {
            'file': file,
            'password': 'password'
        }, follow=True)

        self.assertRedirects(response, reverse('analytics:cas_list'))

        cas_upload = CASUpload.objects.first()

        # Verify Thread was initialized and started
        mock_thread_cls.assert_called_once()
        _, kwargs = mock_thread_cls.call_args
        # kwargs['args'] contains (cas_upload.id, password)
        # We need to extract them
        self.assertEqual(kwargs['args'][0], cas_upload.id)
        self.assertEqual(kwargs['args'][1], 'password')

        # Verify target is process_cas_upload
        # Since it's imported, checking __name__ is safest
        self.assertEqual(kwargs['target'].__name__, 'process_cas_upload')

        mock_thread_instance = mock_thread_cls.return_value
        mock_thread_instance.start.assert_called_once()

class BackgroundTaskTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='taskuser', password='password', user_type=User.Types.INVESTOR)
        self.investor = InvestorProfile.objects.create(user=self.user, pan='ABCDE1234F', firstname='Task', email='task@example.com')

    @patch('apps.analytics.services.tasks.CASParser')
    def test_process_cas_upload_success(self, MockParser):
        # Mock parser behavior
        mock_instance = MockParser.return_value
        mock_instance.parse.return_value = [{
            'scheme_name': "Test Scheme",
            'folio_number': "FOLIO123",
            'isin': "ISIN123",
            'amc_name': "AMC Name",
            'units': Decimal("10.00"),
            'current_value': Decimal("1000.00"),
            'cost_value': Decimal("800.00"),
            'valuation_date': None
        }]

        # Create CASUpload
        from django.core.files.uploadedfile import SimpleUploadedFile
        file = SimpleUploadedFile("test.pdf", b"dummy content", content_type="application/pdf")
        cas_upload = CASUpload.objects.create(
            investor=self.investor,
            uploaded_by=self.user,
            file=file,
            status=CASUpload.STATUS_PENDING
        )

        # Run task synchronously
        process_cas_upload(cas_upload.id, 'password')

        # Verify status updated
        cas_upload.refresh_from_db()
        self.assertEqual(cas_upload.status, CASUpload.STATUS_PROCESSED)

        # Verify holdings created
        self.assertEqual(ExternalHolding.objects.count(), 1)
        holding = ExternalHolding.objects.first()
        self.assertEqual(holding.scheme_name, "Test Scheme")
        self.assertEqual(holding.cas_upload, cas_upload)

    @patch('apps.analytics.services.tasks.CASParser')
    def test_process_cas_upload_failure(self, MockParser):
        # Mock parser failure
        mock_instance = MockParser.return_value
        mock_instance.parse.side_effect = Exception("Parsing Error")

        from django.core.files.uploadedfile import SimpleUploadedFile
        file = SimpleUploadedFile("test.pdf", b"dummy content", content_type="application/pdf")

        cas_upload = CASUpload.objects.create(
            investor=self.investor,
            uploaded_by=self.user,
            file=file,
            status=CASUpload.STATUS_PENDING
        )

        process_cas_upload(cas_upload.id, 'password')

        cas_upload.refresh_from_db()
        self.assertEqual(cas_upload.status, CASUpload.STATUS_FAILED)
        self.assertIn("Parsing Error", cas_upload.error_log)
