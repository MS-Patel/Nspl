from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
import json
from apps.users.models import User, InvestorProfile, DistributorProfile, RMProfile, Branch, BankAccount, Nominee
from apps.products.models import Scheme, AMC, SchemeCategory
from apps.investments.models import Order

class ReportFieldsTest(TestCase):
    def setUp(self):
        # Create Admin User
        self.admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='password', user_type=User.Types.ADMIN)
        self.client = Client()
        self.client.force_login(self.admin)

        # Create Branch
        self.branch = Branch.objects.create(name='Main Branch', code='BR001', city='Mumbai', state='Maharashtra')

        # Create RM
        self.rm_user = User.objects.create_user(username='rm1', email='rm@example.com', password='password', user_type=User.Types.RM)
        self.rm_profile = RMProfile.objects.create(user=self.rm_user, branch=self.branch, employee_code='RM001')

        # Create Distributor
        self.dist_user = User.objects.create_user(username='dist1', email='dist@example.com', password='password', user_type=User.Types.DISTRIBUTOR)
        self.dist_profile = DistributorProfile.objects.create(user=self.dist_user, rm=self.rm_profile, arn_number='ARN-12345', pan='ABCDE1234F', mobile='9876543210')

        # Create Investor
        self.inv_user = User.objects.create_user(username='inv1', email='inv@example.com', password='password', user_type=User.Types.INVESTOR)
        self.inv_profile = InvestorProfile.objects.create(
            user=self.inv_user,
            distributor=self.dist_profile,
            rm=self.rm_profile,
            pan='ABCDE1234G',
            mobile='9876543211',
            tax_status=InvestorProfile.INDIVIDUAL,
            occupation=InvestorProfile.SERVICE,
            holding_nature=InvestorProfile.SINGLE,
            address_1='123 Main St',
            city='Mumbai',
            state='Maharashtra',
            pincode='400001',
            country='India'
        )

        # Create Bank Account
        self.bank = BankAccount.objects.create(
            investor=self.inv_profile,
            bank_name='HDFC Bank',
            account_number='1234567890',
            ifsc_code='HDFC0001234',
            branch_name='Fort',
            is_default=True
        )

        # Create Nominee
        self.nominee = Nominee.objects.create(
            investor=self.inv_profile,
            name='Nominee 1',
            relationship='Spouse',
            percentage=100.00,
            date_of_birth='1990-01-01',
            email='nominee@example.com'
        )

        # Create Scheme
        self.amc = AMC.objects.create(name='HDFC AMC', code='HDFC')
        self.category = SchemeCategory.objects.create(name='Equity', code='EQ')
        self.scheme = Scheme.objects.create(
            amc=self.amc,
            category=self.category,
            name='HDFC Top 100',
            isin='INF179K01BE2',
            scheme_code='HDFC100',
            min_purchase_amount=5000.00,
            unique_no=123456,
            scheme_plan='NORMAL',
            purchase_allowed=True
        )

    def test_distributor_report_fields(self):
        url = reverse('reports:master_report', kwargs={'type': 'distributor'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.context['grid_data_json'])
        self.assertTrue(len(data) > 0)
        row = data[0]
        self.assertIn('email', row)
        self.assertEqual(row['email'], 'dist@example.com')
        self.assertIn('date_joined', row)

    def test_rm_report_fields(self):
        url = reverse('reports:master_report', kwargs={'type': 'rm'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.context['grid_data_json'])
        self.assertTrue(len(data) > 0)
        row = data[0]
        self.assertIn('branch_city', row)
        self.assertEqual(row['branch_city'], 'Mumbai')
        self.assertIn('email', row)

    def test_scheme_report_fields(self):
        url = reverse('reports:master_report', kwargs={'type': 'scheme'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.context['grid_data_json'])
        self.assertTrue(len(data) > 0)
        row = data[0]
        self.assertIn('unique_no', row)
        self.assertEqual(row['unique_no'], 123456)
        self.assertIn('scheme_plan', row)

    def test_bank_report_fields(self):
        url = reverse('reports:master_report', kwargs={'type': 'bank'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.context['grid_data_json'])
        self.assertTrue(len(data) > 0)
        row = data[0]
        self.assertIn('bank_name', row)
        self.assertEqual(row['bank_name'], 'HDFC Bank')
        self.assertIn('investor_name', row)

    def test_nominee_report_fields(self):
        url = reverse('reports:master_report', kwargs={'type': 'nominee'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.context['grid_data_json'])
        self.assertTrue(len(data) > 0)
        row = data[0]
        self.assertIn('nominee_name', row)
        self.assertEqual(row['nominee_name'], 'Nominee 1')
        self.assertIn('email', row)
        self.assertEqual(row['email'], 'nominee@example.com')

    def test_investor_report_fields(self):
        url = reverse('reports:investor_report')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.context['grid_data_json'])
        self.assertTrue(len(data) > 0)
        row = data[0]
        self.assertIn('tax_status', row)
        self.assertEqual(row['tax_status'], 'Individual') # get_display logic
        self.assertIn('address_1', row)
        self.assertEqual(row['address_1'], '123 Main St')
        self.assertIn('city', row)
