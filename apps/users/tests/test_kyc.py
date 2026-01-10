import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.users.models import Document
from apps.users.factories import RMProfileFactory, InvestorProfileFactory, UserFactory
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

@pytest.mark.django_db
class TestKYCDocument:
    def test_document_upload(self, client):
        rm_profile = RMProfileFactory()
        client.force_login(rm_profile.user)

        investor_profile = InvestorProfileFactory()
        url = reverse('investor_detail', args=[investor_profile.pk])

        file_content = b"dummy pdf content"
        test_file = SimpleUploadedFile("test.pdf", file_content, content_type="application/pdf")

        data = {
            'document_type': Document.PAN_CARD,
            'description': 'Test PAN',
            'file': test_file
        }

        response = client.post(url, data)
        assert response.status_code == 302
        assert Document.objects.filter(investor=investor_profile, description='Test PAN').exists()

    def test_toggle_kyc(self, client):
        rm_profile = RMProfileFactory()
        client.force_login(rm_profile.user)

        investor_profile = InvestorProfileFactory(kyc_status=False)
        url = reverse('toggle_kyc', args=[investor_profile.pk])

        # Toggle ON
        response = client.post(url)
        assert response.status_code == 302
        investor_profile.refresh_from_db()
        assert investor_profile.kyc_status is True

        # Toggle OFF
        response = client.post(url)
        assert response.status_code == 302
        investor_profile.refresh_from_db()
        assert investor_profile.kyc_status is False
