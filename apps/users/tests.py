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

        # New Wizard Form Data requires formset management forms
        data = {
            'name': 'Investor One',
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
            'state': 'Maharashtra',
            'pincode': '400001',

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
        }

        response = self.client.post(url, data)
        # Check for errors if 200 (Form Invalid)
        if response.status_code == 200:
            print(response.context['form'].errors)
            if 'bank_accounts' in response.context:
                print(response.context['bank_accounts'].errors)
            if 'nominees' in response.context:
                print(response.context['nominees'].errors)

        self.assertEqual(response.status_code, 302)

        # Check by PAN since username is auto-generated as PAN
        inv = InvestorProfile.objects.get(pan='ABCDE1234F')
        self.assertEqual(inv.distributor.user, dist_user)

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
