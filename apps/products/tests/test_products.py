import pytest
import json
from django.urls import reverse
from django.core.management import call_command
from apps.products.models import Scheme, AMC, SchemeCategory
from apps.products.factories import SchemeFactory, AMCFactory, SchemeCategoryFactory
from apps.users.factories import UserFactory

@pytest.mark.django_db
class TestSchemeModel:
    def test_scheme_creation(self):
        scheme = SchemeFactory()
        assert Scheme.objects.count() == 1
        assert str(scheme) == f"{scheme.name} ({scheme.isin})"

    def test_unique_constraints(self):
        # Test unique Scheme Code
        scheme1 = SchemeFactory(scheme_code="TEST001")
        from django.db.utils import IntegrityError
        # Factory has django_get_or_create, so we use direct object creation to force error
        with pytest.raises(IntegrityError):
             Scheme.objects.create(
                 amc=scheme1.amc,
                 name="Duplicate Scheme",
                 scheme_code="TEST001",
                 isin="IN0000000000"
             )

    def test_amc_creation(self):
        amc = AMCFactory(name="Test AMC", code="TAMC")
        assert amc.name == "Test AMC"
        assert amc.code == "TAMC"

    def test_category_creation(self):
        cat = SchemeCategoryFactory()
        assert cat.name is not None

@pytest.mark.django_db
class TestImportCommand:
    def test_import_command(self):
        # We rely on the sample file created in the previous steps
        # This test ensures the command runs without error and populates the DB
        # Note: If the file doesn't exist, this might fail, but it passed in the previous run.
        # Ideally, we should mock the file or file path, but for migration purposes we keep the logic.
        try:
            call_command('import_schemes')
            assert Scheme.objects.count() > 0
            assert AMC.objects.count() > 0
        except Exception as e:
            # If the file is missing, we skip or fail. The original test didn't handle this, so it assumed file presence.
            pytest.fail(f"Import command failed: {e}")

@pytest.mark.django_db
class TestSchemeView:
    def test_scheme_list_view(self, client):
        user = UserFactory(username='testuser', password='password')
        client.force_login(user)

        scheme = SchemeFactory(name="Test Scheme 1", scheme_code="S001")

        response = client.get(reverse('products:scheme_list'))
        assert response.status_code == 200
        assert 'grid_data_json' in response.context

        data = json.loads(response.context['grid_data_json'])
        assert len(data) >= 1
        # Check if our scheme is in the list (factory might create random names, but we set explicit name)
        found = any(d['name'] == "Test Scheme 1" for d in data)
        assert found
