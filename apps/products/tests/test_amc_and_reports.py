import pytest
from django.urls import reverse
from apps.products.models import AMC, Scheme, SchemeCategory
from django.contrib.auth import get_user_model
import pandas as pd
import io

User = get_user_model()

@pytest.mark.django_db
class TestAMCMaster:
    @pytest.fixture(autouse=True)
    def setup(self, client):
        self.client = client
        self.admin_user = User.objects.create_user(
            username='admin', password='password', user_type=User.Types.ADMIN, is_staff=True
        )
        self.client.force_login(self.admin_user)
        self.amc = AMC.objects.create(name='Test AMC', code='TEST001')

    def test_amc_list_view(self):
        url = reverse('products:amc_list')
        response = self.client.get(url)
        assert response.status_code == 200
        assert b'Test AMC' in response.content
        assert b'TEST001' in response.content

    def test_toggle_amc_status(self):
        url = reverse('products:amc_toggle', args=[self.amc.pk])

        # Initial state
        assert self.amc.is_active is True

        # Toggle to Inactive
        response = self.client.post(url)
        assert response.status_code == 302 # Redirect
        self.amc.refresh_from_db()
        assert self.amc.is_active is False

        # Toggle back to Active
        response = self.client.post(url)
        assert response.status_code == 302
        self.amc.refresh_from_db()
        assert self.amc.is_active is True

    def test_update_amc_name(self):
        url = reverse('products:amc_update', args=[self.amc.pk])
        new_name = "Updated AMC Name"

        # Test update
        response = self.client.post(url, {'name': new_name})
        assert response.status_code == 302

        self.amc.refresh_from_db()
        assert self.amc.name == new_name

        # Test empty name
        response = self.client.post(url, {'name': ''})
        assert response.status_code == 302
        self.amc.refresh_from_db()
        assert self.amc.name == new_name # Should remain unchanged

    def test_scheme_master_export(self):
        category = SchemeCategory.objects.create(name='Equity', code='EQ')
        Scheme.objects.create(
            name='Test Scheme',
            scheme_code='SCH001',
            isin='INF000000000',
            amc=self.amc,
            category=category,
            min_purchase_amount=5000
        )

        url = reverse('products:scheme_master_export')
        response = self.client.get(url)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        # Verify Excel content
        content = response.content
        df = pd.read_excel(io.BytesIO(content))

        assert len(df) == 1
        assert df.iloc[0]['Name'] == 'Test Scheme'
        assert df.iloc[0]['AMC'] == 'Test AMC'
        assert df.iloc[0]['Min Purchase Amount'] == 5000
