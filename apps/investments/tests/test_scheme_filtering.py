import pytest
from django.urls import reverse
from apps.users.factories import UserFactory, InvestorProfileFactory
from apps.products.factories import SchemeFactory, AMCFactory
from rest_framework.test import APIClient

@pytest.mark.django_db
class TestOrderMetadataFiltering:
    def setup_method(self):
        self.user = UserFactory(user_type='INVESTOR')
        # Ensure profile exists
        self.investor_profile = InvestorProfileFactory(user=self.user)
        self.client = APIClient()
        self.client.force_login(self.user)
        self.url = reverse('investments:api_order_metadata')

    def test_inactive_schemes_filtered_out(self):
        """Verify that schemes with amc_active_flag=False are excluded."""
        amc = AMCFactory()
        active_scheme = SchemeFactory(amc=amc, purchase_allowed=True, amc_active_flag=True, name="Active Scheme")
        inactive_scheme = SchemeFactory(amc=amc, purchase_allowed=True, amc_active_flag=False, name="Inactive Scheme")
        purchase_disallowed_scheme = SchemeFactory(amc=amc, purchase_allowed=False, amc_active_flag=True, name="No Purchase")

        response = self.client.get(self.url, {'fetch_schemes': 'true', 'amc_id': amc.id})
        assert response.status_code == 200
        data = response.json()

        schemes = data.get('schemes', [])
        scheme_ids = [s['id'] for s in schemes]

        assert active_scheme.id in scheme_ids
        assert inactive_scheme.id not in scheme_ids
        assert purchase_disallowed_scheme.id not in scheme_ids # Already filtered by purchase_allowed=True

    def test_scheme_flags_returned(self):
        """Verify that is_sip_allowed and is_switch_allowed flags are returned."""
        scheme = SchemeFactory(
            purchase_allowed=True,
            amc_active_flag=True,
            is_sip_allowed=True,
            is_switch_allowed=False
        )

        response = self.client.get(self.url, {'fetch_schemes': 'true', 'scheme_id': scheme.id})
        assert response.status_code == 200
        data = response.json()
        schemes = data.get('schemes', [])

        # Depending on filters, it might return list. If we filter by ID (not supported by view for list directly? view filters by amc/cat/type)
        # The view code: if amc_id... if category_id...
        # It does NOT filter by scheme_id for the list return. It returns all if no filter?
        # Let's use AMC filter to be safe.

        response = self.client.get(self.url, {'fetch_schemes': 'true', 'amc_id': scheme.amc.id})
        data = response.json()
        schemes = data.get('schemes', [])

        target_scheme_data = next((s for s in schemes if s['id'] == scheme.id), None)
        assert target_scheme_data is not None
        assert target_scheme_data['is_sip_allowed'] is True
        assert target_scheme_data['is_switch_allowed'] is False

    def test_sip_allowed_filtering_logic_simulation(self):
        """
        Since we moved filtering to frontend, we just ensure the backend provides enough data
        for the frontend to do its job.
        """
        scheme_sip_yes = SchemeFactory(purchase_allowed=True, amc_active_flag=True, is_sip_allowed=True)
        scheme_sip_no = SchemeFactory(purchase_allowed=True, amc_active_flag=True, is_sip_allowed=False)

        response = self.client.get(self.url, {'fetch_schemes': 'true', 'amc_id': scheme_sip_yes.amc.id})
        data = response.json()
        schemes = data.get('schemes', [])

        # Both should be present in the response
        ids = [s['id'] for s in schemes]
        assert scheme_sip_yes.id in ids
        # scheme_sip_no is in a different AMC? SchemeFactory creates new AMC by default unless passed.

        # Let's put them in same AMC
        amc = AMCFactory()
        s1 = SchemeFactory(amc=amc, purchase_allowed=True, amc_active_flag=True, is_sip_allowed=True)
        s2 = SchemeFactory(amc=amc, purchase_allowed=True, amc_active_flag=True, is_sip_allowed=False)

        response = self.client.get(self.url, {'fetch_schemes': 'true', 'amc_id': amc.id})
        data = response.json()
        schemes = data.get('schemes', [])

        s1_data = next(s for s in schemes if s['id'] == s1.id)
        s2_data = next(s for s in schemes if s['id'] == s2.id)

        assert s1_data['is_sip_allowed'] is True
        assert s2_data['is_sip_allowed'] is False
        # Frontend will filter based on these flags
