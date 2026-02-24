import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from apps.users.models import InvestorProfile, DistributorProfile, RMProfile, Branch

User = get_user_model()

@pytest.mark.django_db
class TestInvestorAPI:

    def setup_method(self):
        # Create Users
        self.admin = User.objects.create_user(username='admin', password='password', user_type=User.Types.ADMIN)
        self.rm_user = User.objects.create_user(username='rm', password='password', user_type=User.Types.RM)
        self.dist_user = User.objects.create_user(username='dist', password='password', user_type=User.Types.DISTRIBUTOR)
        self.investor_user = User.objects.create_user(username='investor', password='password', user_type=User.Types.INVESTOR)
        self.other_investor_user = User.objects.create_user(username='other', password='password', user_type=User.Types.INVESTOR)

        # Create Profiles
        self.branch = Branch.objects.create(name='Main', code='B001')
        self.rm = RMProfile.objects.create(user=self.rm_user, branch=self.branch, employee_code='RM001')
        self.distributor = DistributorProfile.objects.create(user=self.dist_user, rm=self.rm, broker_code='BBF0001', pan='ABCDE1234F')

        # Investor linked to Distributor
        self.investor = InvestorProfile.objects.create(
            user=self.investor_user,
            pan='ABCDE1234G',
            distributor=self.distributor,
            rm=self.rm,
            branch=self.branch
        )

        # Other Investor (Unlinked)
        self.other_investor = InvestorProfile.objects.create(
            user=self.other_investor_user,
            pan='ABCDE1234H'
        )

    def test_list_investors_admin(self, api_client):
        api_client.force_authenticate(user=self.admin)
        response = api_client.get('/api/investors/')
        assert response.status_code == status.HTTP_200_OK
        # Admin sees both
        data = response.data.get('results') if isinstance(response.data, dict) else response.data
        assert len(data) == 2

    def test_list_investors_distributor(self, api_client):
        api_client.force_authenticate(user=self.dist_user)
        response = api_client.get('/api/investors/')
        assert response.status_code == status.HTTP_200_OK
        # Distributor sees only their investor
        data = response.data.get('results') if isinstance(response.data, dict) else response.data
        assert len(data) == 1
        assert data[0]['id'] == self.investor.id

    def test_list_investors_rm(self, api_client):
        api_client.force_authenticate(user=self.rm_user)
        response = api_client.get('/api/investors/')
        assert response.status_code == status.HTTP_200_OK
        # RM sees their investor (via distributor)
        data = response.data.get('results') if isinstance(response.data, dict) else response.data
        assert len(data) == 1
        assert data[0]['id'] == self.investor.id

    def test_retrieve_investor_detail_distributor_success(self, api_client):
        api_client.force_authenticate(user=self.dist_user)
        response = api_client.get(f'/api/investors/{self.investor.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == self.investor.id

    def test_retrieve_investor_detail_distributor_denied(self, api_client):
        api_client.force_authenticate(user=self.dist_user)
        response = api_client.get(f'/api/investors/{self.other_investor.id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
