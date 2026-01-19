import pytest
from django.urls import reverse
from apps.users.models import InvestorProfile
from apps.users.factories import InvestorProfileFactory, UserFactory, DistributorProfileFactory
from unittest.mock import patch, MagicMock

@pytest.mark.django_db
class TestNomineeAuth:

    def setup_method(self):
        # Create a Distributor User (who has permission)
        self.distributor_user = UserFactory(user_type='DISTRIBUTOR')
        self.distributor_profile = DistributorProfileFactory(user=self.distributor_user)

        # Create an Investor with UCC
        self.investor = InvestorProfileFactory(
            distributor=self.distributor_profile,
            ucc_code='TESTUCC123',
            nominee_auth_status=InvestorProfile.AUTH_PENDING, # Initial State
            nomination_opt='Y',
            nomination_auth_mode='O' # Online
        )

    def test_trigger_nominee_auth_view_success(self, client):
        """
        Test that triggering auth calls the BSE client and updates status based on response.
        """
        client.force_login(self.distributor_user)
        url = reverse('users:trigger_nominee_auth', args=[self.investor.pk])

        # Mock Validation to pass
        with patch('apps.users.views.validate_investor_for_bse', return_value=[]):
            # Mock the BSE Client
            with patch('apps.users.views.BSEStarMFClient') as MockClient:
                mock_instance = MockClient.return_value
                mock_instance.register_client.return_value = {
                    'status': 'success',
                    'remarks': 'CLIENT NOMINEE AUTHENTICATED SUCCESSFULLY'
                }

                response = client.post(url, follow=True)

                # Assertions
                assert response.status_code == 200
                self.investor.refresh_from_db()
                assert self.investor.nominee_auth_status == InvestorProfile.AUTH_AUTHENTICATED
                assert "AUTHENTICATED" in self.investor.bse_remarks

    def test_trigger_nominee_auth_view_pending(self, client):
        """
        Test parsing of 'Pending' status from remarks.
        """
        client.force_login(self.distributor_user)
        url = reverse('users:trigger_nominee_auth', args=[self.investor.pk])

        with patch('apps.users.views.validate_investor_for_bse', return_value=[]):
            with patch('apps.users.views.BSEStarMFClient') as MockClient:
                mock_instance = MockClient.return_value
                mock_instance.register_client.return_value = {
                    'status': 'success',
                    'remarks': 'NOMINEE AUTHENTICATION PENDING'
                }

                response = client.post(url, follow=True)

                self.investor.refresh_from_db()
                assert self.investor.nominee_auth_status == InvestorProfile.AUTH_PENDING

    def test_compliance_guard_blocks_order(self):
        """
        Test that place_order blocks if Nominee Auth is Pending.
        """
        from apps.integration.bse_client import BSEStarMFClient

        # Ensure investor is Pending
        self.investor.nominee_auth_status = InvestorProfile.AUTH_PENDING
        self.investor.save()

        # Mock Order Object
        mock_order = MagicMock()
        mock_order.investor = self.investor
        mock_order.unique_ref_no = "12345"

        client = BSEStarMFClient()

        # Attempt Place Order
        response = client.place_order(mock_order)

        assert response['status'] == 'error'
        assert "COMPLIANCE BLOCK" in response['remarks']
        assert "Nominee Authentication is Pending" in response['remarks']

    def test_compliance_guard_allows_authenticated(self):
        """
        Test that place_order proceeds if Nominee Auth is Authenticated.
        """
        from apps.integration.bse_client import BSEStarMFClient

        self.investor.nominee_auth_status = InvestorProfile.AUTH_AUTHENTICATED
        self.investor.save()

        mock_order = MagicMock()
        mock_order.investor = self.investor
        mock_order.unique_ref_no = "12345"
        mock_order.amount = 1000
        mock_order.units = 10
        mock_order.scheme.scheme_code = 'INF123'

        client = BSEStarMFClient()

        # Mock Internal Auth and SOAP
        with patch.object(client, '_get_auth_details', return_value=('encrypted', 'passkey')):
            with patch.object(client, '_get_soap_client') as mock_soap:
                mock_soap.return_value.service.orderEntryParam.return_value = "0|123|Success"

                response = client.place_order(mock_order)

                assert response['status'] == 'success'
