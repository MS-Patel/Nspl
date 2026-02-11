import pytest
from unittest.mock import MagicMock, patch
from apps.integration.bse_client import BSEStarMFClient
from apps.users.models import InvestorProfile, Nominee, User
from django.core.management import call_command
import json

@pytest.mark.django_db
class TestNomineeFlags:

    def setup_method(self):
        self.user = User.objects.create(username='testuser', email='test@example.com')
        self.investor = InvestorProfile.objects.create(
            user=self.user,
            pan='ABCDE1234F',
            ucc_code='TEST001',
            nomination_opt='Y'
        )
        self.nominee = Nominee.objects.create(
            investor=self.investor,
            name='Test Nominee',
            percentage=100,
            mobile='', # Missing mobile
            email=''   # Missing email
        )

    def test_bulk_update_client_method(self):
        client = BSEStarMFClient()
        # Override URL to avoid real network call if mock fails (safety)
        client.nominee_api_url = "http://mock-url"

        investor_list = [{'client_code': 'TEST001'}, {'client_code': 'TEST002'}]

        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"Status": "0", "Remarks": "Success"}
            mock_response.text = '{"Status": "0", "Remarks": "Success"}'
            mock_post.return_value = mock_response

            result = client.bulk_update_nominee_flags(investor_list)

            assert result['status'] == "success"
            assert result['data']['Status'] == "0"
            mock_post.assert_called_once()

            # Verify payload structure
            args, kwargs = mock_post.call_args
            payload = kwargs['json']
            assert payload['req_type'] == 'nom_flag'
            assert len(payload['req_array']) == 2
            assert payload['req_array'][0]['client_code'] == 'TEST001'
            assert payload['req_array'][0]['nom_flag'] == 'N'

    def test_management_command_logic(self):
        # Create another investor who should NOT be picked (has valid details)
        user2 = User.objects.create(username='validuser', email='valid@example.com')
        inv2 = InvestorProfile.objects.create(
            user=user2,
            pan='FGHIJ5678K',
            ucc_code='TEST002',
            nomination_opt='Y'
        )
        Nominee.objects.create(
            investor=inv2,
            name='Valid Nominee',
            percentage=100,
            mobile='9876543210',
            email='valid@test.com'
        )

        # Create an investor who should NOT be picked (nomination_opt='N')
        user3 = User.objects.create(username='nouser', email='no@example.com')
        inv3 = InvestorProfile.objects.create(
            user=user3,
            pan='KLMNO1234P',
            ucc_code='TEST003',
            nomination_opt='N'
        )
        # Even if they have a nominee with missing details (data inconsistency),
        # the command filters on nomination_opt='Y'.
        Nominee.objects.create(
            investor=inv3,
            name='Ghost Nominee',
            percentage=100,
            mobile='',
            email=''
        )

        with patch('apps.integration.management.commands.update_nominee_flags.BSEStarMFClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.bulk_update_nominee_flags.return_value = {"status": "success", "data": {"Status": "0"}}

            call_command('update_nominee_flags')

            # Should have called bulk_update once with 1 investor (our setup_method investor)
            mock_instance.bulk_update_nominee_flags.assert_called_once()
            call_args = mock_instance.bulk_update_nominee_flags.call_args[0][0]

            # Verify passed list
            assert len(call_args) == 1
            assert call_args[0].ucc_code == 'TEST001'
