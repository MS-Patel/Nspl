import pytest
from django.urls import reverse
from apps.users.models import User, InvestorProfile, Nominee
from apps.integration.utils import map_investor_to_bse_param_string
from unittest.mock import patch

@pytest.mark.django_db
class TestOptOutNominee:

    @pytest.fixture
    def admin_user(self):
        return User.objects.create_user(username='admin', password='password', user_type=User.Types.ADMIN)

    @pytest.fixture
    def rm_user(self):
        return User.objects.create_user(username='rm', password='password', user_type=User.Types.RM)

    @pytest.fixture
    def distributor_user(self):
        return User.objects.create_user(username='dist', password='password', user_type=User.Types.DISTRIBUTOR)

    @pytest.fixture
    def investor_user(self):
        return User.objects.create_user(username='investor', password='password', user_type=User.Types.INVESTOR, name='John Doe')

    @pytest.fixture
    def investor_profile(self, investor_user):
        profile = InvestorProfile.objects.create(
            user=investor_user,
            pan='ABCDE1234F',
            nomination_opt='Y',
            nominee_auth_status=InvestorProfile.AUTH_AUTHENTICATED,
            ucc_code='12345'
        )
        Nominee.objects.create(investor=profile, name='Nominee 1', percentage=100, relationship='Father')
        return profile

    def test_map_investor_to_bse_param_string_nominees(self, investor_profile):
        # Case 1: Opt = Y -> Should verify nominee details are present
        param_string_y = map_investor_to_bse_param_string(investor_profile)
        parts_y = param_string_y.split('|')
        # Nominee Name is at Field 124 (Index 123)
        assert parts_y[123] == 'Nominee 1'

        # Case 2: Opt = N -> Should verify nominee details are blank
        investor_profile.nomination_opt = 'N'
        investor_profile.save()

        param_string_n = map_investor_to_bse_param_string(investor_profile)
        parts_n = param_string_n.split('|')
        # Nominee Name should be empty
        assert parts_n[123] == ''

    def test_view_permissions(self, client, admin_user, rm_user, distributor_user, investor_user, investor_profile):
        url = reverse('users:opt_out_nominee', args=[investor_profile.pk])

        # Admin - Success (Mock BSE)
        client.force_login(admin_user)
        with patch('apps.users.views.BSEStarMFClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.bulk_update_nominee_flags.return_value = {'status': 'success', 'remarks': 'Updated', 'data': {}}

            response = client.post(url)
            assert response.status_code == 302
            investor_profile.refresh_from_db()
            assert investor_profile.nomination_opt == 'N'
            assert investor_profile.nominee_auth_status == InvestorProfile.AUTH_NOT_AVAILABLE

        # Reset
        investor_profile.nomination_opt = 'Y'
        investor_profile.save()

        # RM - Success
        client.force_login(rm_user)
        with patch('apps.users.views.BSEStarMFClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.bulk_update_nominee_flags.return_value = {'status': 'success', 'remarks': 'Updated', 'data': {}}

            response = client.post(url)
            assert response.status_code == 302
            investor_profile.refresh_from_db()
            assert investor_profile.nomination_opt == 'N'

        # Distributor - Fail
        client.force_login(distributor_user)
        response = client.post(url)
        assert response.status_code == 302 # Redirects with error message, but view handles permission check manually and redirects
        # Check messages? Or simply verify state didn't change (if we reset)

        # Reset
        investor_profile.nomination_opt = 'Y'
        investor_profile.save()

        client.force_login(distributor_user)
        response = client.post(url)
        investor_profile.refresh_from_db()
        assert investor_profile.nomination_opt == 'Y' # Should NOT change

        # Investor - Fail
        client.force_login(investor_user)
        response = client.post(url)
        investor_profile.refresh_from_db()
        assert investor_profile.nomination_opt == 'Y' # Should NOT change

    def test_view_bse_call(self, client, admin_user, investor_profile):
        url = reverse('users:opt_out_nominee', args=[investor_profile.pk])
        client.force_login(admin_user)

        with patch('apps.users.views.BSEStarMFClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.bulk_update_nominee_flags.return_value = {'status': 'success', 'remarks': 'Updated', 'data': {}}

            client.post(url)

            # Verify bulk_update_nominee_flags was called
            assert mock_instance.bulk_update_nominee_flags.called
            args, kwargs = mock_instance.bulk_update_nominee_flags.call_args

            # Verify the argument is a list containing the investor
            investor_list = args[0]
            assert len(investor_list) == 1
            assert investor_list[0].pk == investor_profile.pk

            # Verify register_client was NOT called
            assert not mock_instance.register_client.called
