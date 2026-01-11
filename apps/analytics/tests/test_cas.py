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
