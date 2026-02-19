from django.test import TestCase, Client
from django.urls import reverse
from apps.users.models import User, InvestorProfile, DistributorProfile, RMProfile, Branch

class InvestorPermissionTests(TestCase):
    def setUp(self):
        # Create Users
        self.admin_user = User.objects.create_user(username='admin', password='password', user_type=User.Types.ADMIN)
        self.rm_user = User.objects.create_user(username='rm', password='password', user_type=User.Types.RM)
        self.dist_user = User.objects.create_user(username='dist', password='password', user_type=User.Types.DISTRIBUTOR)
        self.investor_user = User.objects.create_user(username='investor', password='password', user_type=User.Types.INVESTOR)
        self.other_investor_user = User.objects.create_user(username='other_investor', password='password', user_type=User.Types.INVESTOR)

        # Create Profiles
        self.branch = Branch.objects.create(name="Main Branch", code="MB001")
        self.rm_profile = RMProfile.objects.create(user=self.rm_user, employee_code="RM001", branch=self.branch)
        self.dist_profile = DistributorProfile.objects.create(user=self.dist_user, arn_number="ARN001", rm=self.rm_profile)

        # Investor 1 (Linked to Dist -> RM)
        self.investor_profile = InvestorProfile.objects.create(
            user=self.investor_user,
            pan="ABCDE1234F",
            distributor=self.dist_profile,
            rm=self.rm_profile,
            branch=self.branch,
            dob="1990-01-01"
        )

        # Investor 2 (Independent / Other Dist)
        self.other_investor_profile = InvestorProfile.objects.create(
            user=self.other_investor_user,
            pan="FGHIJ5678K",
            dob="1990-01-01"
        )

        self.client = Client()

    def test_investor_detail_access(self):
        url = reverse('users:investor_detail', args=[self.investor_profile.pk])

        # 1. Admin Access (Allowed)
        self.client.login(username='admin', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # 2. Owner Investor Access (Allowed)
        self.client.login(username='investor', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_investor_list_access(self):
        url = reverse('users:investor_list')

        # 1. Admin Access (Allowed)
        self.client.login(username='admin', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # 2. Investor Access (Forbidden)
        self.client.login(username='investor', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # 3. Other Investor Access (Forbidden)
        self.client.login(username='other_investor', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # 4. Distributor Access (Allowed - Linked)
        self.client.login(username='dist', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # 5. RM Access (Allowed - Linked)
        self.client.login(username='rm', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_investor_create_access(self):
        url = reverse('users:investor_create')

        # 1. Admin Access (Allowed)
        self.client.login(username='admin', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # 2. Investor Access (Forbidden)
        self.client.login(username='investor', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_investor_update_access(self):
        url = reverse('users:investor_update', args=[self.investor_profile.pk])

        # 1. Other Investor Access (Forbidden)
        self.client.login(username='other_investor', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # 2. Owner Investor Access (Allowed)
        self.client.login(username='investor', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
