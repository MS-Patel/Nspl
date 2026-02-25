from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.users.models import InvestorProfile, DistributorProfile, RMProfile
from apps.investments.models import Mandate
from apps.users.factories import (
    UserFactory, RMUserFactory, DistributorUserFactory, InvestorUserFactory,
    RMProfileFactory, DistributorProfileFactory, InvestorProfileFactory,
    BankAccountFactory, NomineeFactory
)
import datetime

User = get_user_model()

class InvestorListAPIViewTests(APITestCase):
    def setUp(self):
        # Admin
        self.admin = UserFactory(username='admin', user_type=User.Types.ADMIN)
        self.admin.user_type = User.Types.ADMIN
        self.admin.save()

        # RM
        self.rm_user = RMUserFactory(username='rm_user')
        self.rm_profile = RMProfileFactory(user=self.rm_user)

        # Distributor under RM
        self.dist_user = DistributorUserFactory(username='dist_user')
        self.dist_profile = DistributorProfileFactory(user=self.dist_user, rm=self.rm_profile)

        # Investors
        # Investor 1: Linked to Distributor (so linked to RM)
        self.inv1_user = InvestorUserFactory(username='inv1', name='Alice Investor', email='alice@example.com')
        self.inv1_profile = InvestorProfileFactory(user=self.inv1_user, distributor=self.dist_profile, pan='ABCDE1234F')

        # Investor 2: Direct RM (no distributor, but RM is assigned) - Wait, logic says (distributor__rm=user) OR (rm=user)
        self.inv2_user = InvestorUserFactory(username='inv2', name='Bob Investor', email='bob@example.com')
        self.inv2_profile = InvestorProfileFactory(user=self.inv2_user, distributor=None, rm=self.rm_profile, pan='FGHIJ5678K')

        # Investor 3: Unrelated (Other Distributor, Other RM)
        self.other_dist = DistributorProfileFactory(user=DistributorUserFactory(username='other_dist'), rm=None)
        self.inv3_user = InvestorUserFactory(username='inv3', name='Charlie Investor')
        self.inv3_profile = InvestorProfileFactory(user=self.inv3_user, distributor=self.other_dist, pan='KLMNO9012P')

        self.url = reverse('users:api_investor_list')

    def test_admin_sees_all_investors(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see all 3
        self.assertEqual(response.data['count'], 3)

    def test_rm_sees_linked_investors(self):
        self.client.force_authenticate(user=self.rm_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see inv1 (via distributor) and inv2 (direct)
        # inv3 is unrelated
        results = response.data['results']
        ids = [r['id'] for r in results]
        self.assertIn(self.inv1_profile.id, ids)
        self.assertIn(self.inv2_profile.id, ids)
        self.assertNotIn(self.inv3_profile.id, ids)
        self.assertEqual(len(ids), 2)

    def test_distributor_sees_own_investors(self):
        self.client.force_authenticate(user=self.dist_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see only inv1
        results = response.data['results']
        ids = [r['id'] for r in results]
        self.assertIn(self.inv1_profile.id, ids)
        self.assertNotIn(self.inv2_profile.id, ids)
        self.assertNotIn(self.inv3_profile.id, ids)
        self.assertEqual(len(ids), 1)

    def test_search_functionality(self):
        self.client.force_authenticate(user=self.admin)

        # Search by Name
        response = self.client.get(self.url, {'search': 'Alice'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'Alice Investor')

        # Search by PAN
        response = self.client.get(self.url, {'search': 'ABCDE1234F'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['pan'], 'ABCDE1234F')

        # Search by Email
        response = self.client.get(self.url, {'search': 'bob@example.com'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['email'], 'bob@example.com')

    def test_pagination(self):
        self.client.force_authenticate(user=self.admin)
        # Create 15 investors
        for i in range(15):
             u = InvestorUserFactory(username=f'p_inv_{i}')
             InvestorProfileFactory(user=u, distributor=self.dist_profile)

        # Total = 3 (from setUp) + 15 = 18
        response = self.client.get(self.url)
        self.assertEqual(response.data['count'], 18)
        self.assertEqual(len(response.data['results']), 10) # Page size 10
        self.assertIsNotNone(response.data['next'])

class InvestorDetailAPIViewTests(APITestCase):
    def setUp(self):
        self.admin = UserFactory(username='admin', user_type=User.Types.ADMIN)
        self.admin.user_type = User.Types.ADMIN
        self.admin.save()

        self.user = InvestorUserFactory(username='detail_user', name='Detail User')
        self.profile = InvestorProfileFactory(
            user=self.user,
            pan='ABCDE1234F',
            place_of_birth='Mumbai',
            country_of_birth='India',
            source_of_wealth='01', # Salary
            income_slab='32', # 1-5L
            pep_status='N',
            foreign_address_1='123 Foreign St',
            second_applicant_name='Jane Doe'
        )

        # Create related objects
        self.bank = BankAccountFactory(investor=self.profile, bank_name='HDFC', account_number='1234567890')
        self.nominee = NomineeFactory(investor=self.profile, name='Nominee 1')
        self.mandate = Mandate.objects.create(
            investor=self.profile,
            mandate_id='UMRN123456',
            amount_limit=10000,
            start_date=datetime.date.today(),
            bank_account=self.bank
        )

        self.url = reverse('users:api_investor_detail', kwargs={'pk': self.profile.pk})

    def test_detail_view_returns_nested_data(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        # Check Basic Fields
        self.assertEqual(data['name'], 'Detail User')
        self.assertEqual(data['pan'], 'ABCDE1234F')

        # Check Nested Data
        self.assertEqual(len(data['bank_accounts']), 1)
        self.assertEqual(data['bank_accounts'][0]['bank_name'], 'HDFC')

        self.assertEqual(len(data['nominees']), 1)
        self.assertEqual(data['nominees'][0]['name'], 'Nominee 1')

        self.assertEqual(len(data['mandates']), 1)
        self.assertEqual(data['mandates'][0]['mandate_id'], 'UMRN123456')

        # Check FATCA Fields
        self.assertEqual(data['place_of_birth'], 'Mumbai')
        self.assertEqual(data['source_of_wealth'], '01')
        self.assertEqual(data['pep_status'], 'N')

        # Check Foreign Address
        self.assertEqual(data['foreign_address_1'], '123 Foreign St')

        # Check Joint Holders
        self.assertEqual(data['second_applicant_name'], 'Jane Doe')
