import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.users.models import RMProfile, DistributorProfile, InvestorProfile
from apps.users.factories import (
    UserFactory, RMProfileFactory, DistributorProfileFactory, InvestorProfileFactory
)

User = get_user_model()

@pytest.mark.django_db
class TestUserCreation:
    def test_rm_creation(self, client):
        # Admin creates RM
        admin = User.objects.create_superuser(username='admin', password='password', user_type=User.Types.ADMIN)
        client.force_login(admin)

        url = reverse('users:rm_create')
        data = {
            'email': 'rm1@example.com',
            'name': 'RM One',
            'employee_code': 'EMP001',
            'pan': 'ABCDE1234F',
            'is_active': True
        }
        response = client.post(url, data)
        if response.status_code != 302:
            print(response.context['form'].errors)

        assert response.status_code == 302
        assert User.objects.filter(username='EMP001').exists()
        rm_user = User.objects.get(username='EMP001')
        assert rm_user.check_password('ABCDE1234F')
        assert RMProfile.objects.filter(user=rm_user, employee_code='EMP001').exists()

    def test_distributor_creation(self, client):
        rm_profile = RMProfileFactory()
        client.force_login(rm_profile.user)

        url = reverse('users:distributor_create')
        data = {
            'email': 'dist1@example.com',
            'name': 'Dist One',
            'arn_number': 'ARN-12345',
            'mobile': '9999999999',
            'pan': 'FGHIJ5678K',
            'is_active': True
        }
        response = client.post(url, data)
        if response.status_code != 302:
            print(response.context['form'].errors)

        assert response.status_code == 302

        # Since broker_code is auto-generated, we find by email or logic
        dist = DistributorProfile.objects.get(user__email='dist1@example.com')
        assert dist.rm == rm_profile
        assert dist.arn_number == 'ARN-12345'
        assert dist.user.username.startswith('BBF')
        assert dist.user.check_password('FGHIJ5678K')

    def test_investor_creation(self, client):
        dist_profile = DistributorProfileFactory()
        client.force_login(dist_profile.user)

        url = reverse('users:investor_create')

        # New Wizard Form Data requires formset management forms
        data = {
            'firstname': 'Investor',
            'lastname': 'One',
            'email': 'inv1@example.com',
            'pan': 'ABCDE1234F',
            'dob': '1990-01-01',
            'gender': 'M',
            'mobile': '8888888888',
            'tax_status': '01',
            'occupation': '02',
            'holding_nature': 'SI',
            'address_1': 'Test Address',
            'city': 'Mumbai',
            'state': 'MAHARASHTRA',
            'pincode': '400001',
            'country': 'India',

            # Default V183 fields
            'kyc_type': 'K',
            'mobile_declaration': 'SE',
            'email_declaration': 'SE',
            'paperless_flag': 'P',
            'second_applicant_email_declaration': 'SE',
            'second_applicant_mobile_declaration': 'SE',
            'third_applicant_email_declaration': 'SE',
            'third_applicant_mobile_declaration': 'SE',
            'client_type': 'P',
            'nomination_opt': 'Y',

            # FATCA Fields
            'place_of_birth': 'Mumbai',
            'country_of_birth': 'India',
            'source_of_wealth': '01',
            'income_slab': '32',
            'pep_status': 'N',
            'exemption_code': 'N',

            # Management Forms for Formsets
            'bank_accounts-TOTAL_FORMS': '1',
            'bank_accounts-INITIAL_FORMS': '0',
            'bank_accounts-MIN_NUM_FORMS': '0',
            'bank_accounts-MAX_NUM_FORMS': '1000',

            'nominees-TOTAL_FORMS': '1',
            'nominees-INITIAL_FORMS': '0',
            'nominees-MIN_NUM_FORMS': '0',
            'nominees-MAX_NUM_FORMS': '1000',

            # Formset Data (Bank)
            'bank_accounts-0-ifsc_code': 'HDFC0001234',
            'bank_accounts-0-account_number': '1234567890',
            'bank_accounts-0-account_type': 'SB',
            'bank_accounts-0-bank_name': 'HDFC Bank',
            'bank_accounts-0-branch_name': 'Mumbai',

            # Formset Data (Nominee)
            'nominees-0-name': 'Nominee One',
            'nominees-0-relationship': 'Spouse',
            'nominees-0-percentage': '100',
            'nominees-0-address_1': 'Nominee Addr',
            'nominees-0-city': 'Mumbai',
            'nominees-0-state': 'MAHARASHTRA',
            'nominees-0-pincode': '400001',
        }

        response = client.post(url, data)

        # Debugging output if validation fails
        if response.status_code == 200:
             print(response.context['form'].errors)
             # print(response.context['bank_accounts'].errors)
             # print(response.context['nominees'].errors)

        assert response.status_code == 302

        # Check by PAN
        inv = InvestorProfile.objects.get(pan='ABCDE1234F')
        assert inv.distributor == dist_profile

@pytest.mark.django_db
class TestAccessControl:
    def test_rm_dashboard_access(self, client):
        rm_profile = RMProfileFactory()
        dist_profile = DistributorProfileFactory()

        client.force_login(rm_profile.user)
        response = client.get(reverse('users:rm_dashboard'))
        assert response.status_code == 200

        client.force_login(dist_profile.user)
        response = client.get(reverse('users:rm_dashboard'))
        assert response.status_code == 403

@pytest.mark.django_db
class TestFATCAUpload:
    def test_fatca_upload_view(self, client):
        """
        Test that FATCA Upload view works correctly and calls the BSE Client.
        """
        # 1. Setup Data
        rm_profile = RMProfileFactory()
        client.force_login(rm_profile.user)

        investor = InvestorProfileFactory(ucc_code="12345678")
        url = reverse('users:fatca_upload', args=[investor.pk])

        # 2. Mock BSE Client
        with patch('apps.users.views.BSEStarMFClient') as MockBSEClient:
            mock_client_instance = MockBSEClient.return_value
            mock_client_instance.fatca_upload.return_value = {
                'status': 'success',
                'remarks': 'FATCA Uploaded Successfully'
            }

            # 3. Perform Request
            response = client.post(url)

            # 4. Assertions
            assert response.status_code == 302 # Redirects back
            mock_client_instance.fatca_upload.assert_called_once_with(investor)

            # Verify message (using django messages framework in test)
            messages = list(response.wsgi_request._messages)
            assert len(messages) == 1
            assert str(messages[0]) == "FATCA Upload Successful: FATCA Uploaded Successfully"

    def test_fatca_upload_no_ucc(self, client):
        """
        Test that FATCA Upload fails if UCC is missing.
        """
        rm_profile = RMProfileFactory()
        client.force_login(rm_profile.user)

        investor = InvestorProfileFactory(ucc_code=None)
        url = reverse('users:fatca_upload', args=[investor.pk])

        with patch('apps.users.views.BSEStarMFClient') as MockBSEClient:
             response = client.post(url)

             assert response.status_code == 302
             MockBSEClient.return_value.fatca_upload.assert_not_called()

             messages = list(response.wsgi_request._messages)
             assert "Investor must have a UCC Code" in str(messages[0])
