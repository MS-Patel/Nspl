from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import RMProfile, DistributorProfile, InvestorProfile

User = get_user_model()

class UserCreationTests(TestCase):
    def setUp(self):
        # Create an Admin user
        self.admin = User.objects.create_superuser(username='admin', password='password', user_type=User.Types.ADMIN)
        self.client = Client()

    def test_rm_creation(self):
        self.client.force_login(self.admin)
        url = reverse('rm_create')
        data = {
            'username': 'rm1',
            'email': 'rm1@example.com',
            'name': 'RM One',
            'password': 'password',
            'confirm_password': 'password',
            'employee_code': 'EMP001'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # Redirects on success

        self.assertTrue(User.objects.filter(username='rm1').exists())
        self.assertTrue(RMProfile.objects.filter(user__username='rm1', employee_code='EMP001').exists())

    def test_distributor_creation(self):
        # First create an RM
        rm_user = User.objects.create_user(username='rm2', password='password', user_type=User.Types.RM)
        RMProfile.objects.create(user=rm_user, employee_code='EMP002')

        # Admin creates Distributor assigned to RM
        self.client.force_login(rm_user) # Login as RM
        url = reverse('distributor_create')
        data = {
            'username': 'dist1',
            'email': 'dist1@example.com',
            'name': 'Dist One',
            'password': 'password',
            'confirm_password': 'password',
            'arn_number': 'ARN-12345',
            'mobile': '9999999999'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        dist = DistributorProfile.objects.get(user__username='dist1')
        self.assertEqual(dist.rm.user, rm_user)
        self.assertEqual(dist.arn_number, 'ARN-12345')

    def test_investor_creation(self):
        # Setup Distributor
        dist_user = User.objects.create_user(username='dist2', password='password', user_type=User.Types.DISTRIBUTOR)
        DistributorProfile.objects.create(user=dist_user, arn_number='ARN-67890')

        self.client.force_login(dist_user)
        url = reverse('investor_create')
        data = {
            'username': 'inv1',
            'email': 'inv1@example.com',
            'name': 'Investor One',
            'password': 'password',
            'confirm_password': 'password',
            'pan': 'ABCDE1234F',
            'mobile': '8888888888'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        inv = InvestorProfile.objects.get(user__username='inv1')
        self.assertEqual(inv.distributor.user, dist_user)
        self.assertEqual(inv.pan, 'ABCDE1234F')

class AccessControlTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(username='admin', password='password', user_type=User.Types.ADMIN)
        self.rm = User.objects.create_user(username='rm', password='password', user_type=User.Types.RM)
        RMProfile.objects.create(user=self.rm, employee_code='EMP999')
        self.dist = User.objects.create_user(username='dist', password='password', user_type=User.Types.DISTRIBUTOR)
        DistributorProfile.objects.create(user=self.dist, arn_number='ARN-999')

    def test_rm_dashboard_access(self):
        self.client.force_login(self.rm)
        response = self.client.get(reverse('rm_dashboard'))
        self.assertEqual(response.status_code, 200)

        # Distributor cannot access RM dashboard
        self.client.force_login(self.dist)
        response = self.client.get(reverse('rm_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_create_rm_permission(self):
        # RM cannot create another RM
        self.client.force_login(self.rm)
        response = self.client.get(reverse('rm_create'))
        self.assertEqual(response.status_code, 403)
