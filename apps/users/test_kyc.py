from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.users.models import InvestorProfile, Document, RMProfile

User = get_user_model()

class KYCDocumentTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.rm_user = User.objects.create_user(username='rm_user', password='password', user_type=User.Types.RM)
        RMProfile.objects.create(user=self.rm_user, employee_code='EMP001')

        self.investor_user = User.objects.create_user(username='investor', password='password', user_type=User.Types.INVESTOR)
        self.investor_profile = InvestorProfile.objects.create(
            user=self.investor_user,
            pan='ABCDE1234F',
            dob='1990-01-01',
            mobile='9999999999'
        )

    def test_document_upload(self):
        self.client.force_login(self.rm_user)
        url = reverse('investor_detail', args=[self.investor_profile.pk])

        from django.core.files.uploadedfile import SimpleUploadedFile
        file_content = b"dummy pdf content"
        test_file = SimpleUploadedFile("test.pdf", file_content, content_type="application/pdf")

        data = {
            'document_type': Document.PAN_CARD,
            'description': 'Test PAN',
            'file': test_file
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # Redirect

        self.assertTrue(Document.objects.filter(investor=self.investor_profile, description='Test PAN').exists())

    def test_toggle_kyc(self):
        self.client.force_login(self.rm_user)
        url = reverse('toggle_kyc', args=[self.investor_profile.pk])

        # Initial State: False
        self.assertFalse(self.investor_profile.kyc_status)

        # Toggle ON
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.investor_profile.refresh_from_db()
        self.assertTrue(self.investor_profile.kyc_status)

        # Toggle OFF
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.investor_profile.refresh_from_db()
        self.assertFalse(self.investor_profile.kyc_status)
