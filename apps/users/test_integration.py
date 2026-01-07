from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import RMProfile, DistributorProfile, InvestorProfile

User = get_user_model()

class AuthenticationIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(username='admin', password='password', user_type=User.Types.ADMIN)
        self.rm = User.objects.create_user(username='rm', password='password', user_type=User.Types.RM)
        RMProfile.objects.create(user=self.rm, employee_code='EMP999')
        self.dist = User.objects.create_user(username='dist', password='password', user_type=User.Types.DISTRIBUTOR)
        DistributorProfile.objects.create(user=self.dist, arn_number='ARN-999')
        self.investor = User.objects.create_user(username='investor', password='password', user_type=User.Types.INVESTOR)

    def test_login_redirects(self):
        # Admin Login
        response = self.client.post(reverse('login'), {'username': 'admin', 'password': 'password'})
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.client.logout()

        # RM Login
        response = self.client.post(reverse('login'), {'username': 'rm', 'password': 'password'})
        self.assertRedirects(response, reverse('rm_dashboard'))
        # Verify user is authenticated and can access dashboard
        response = self.client.get(reverse('rm_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # Distributor Login
        response = self.client.post(reverse('login'), {'username': 'dist', 'password': 'password'})
        self.assertRedirects(response, reverse('distributor_dashboard'))
        self.client.logout()

        # Investor Login
        response = self.client.post(reverse('login'), {'username': 'investor', 'password': 'password'})
        self.assertRedirects(response, reverse('investor_dashboard'))
        self.client.logout()

    def test_navigation_menu_visibility(self):
        # Admin should see RM and Distributor links
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<span>Masters</span>')
        self.assertContains(response, reverse('rm_list'))
        self.assertContains(response, reverse('distributor_list'))

        # RM should see Distributor link
        self.client.force_login(self.rm)
        response = self.client.get(reverse('rm_dashboard'))
        self.assertContains(response, '<span>Masters</span>')
        self.assertContains(response, reverse('distributor_list'))
        self.assertNotContains(response, reverse('rm_list'))

        # Distributor should NOT see Masters dropdown
        self.client.force_login(self.dist)
        response = self.client.get(reverse('distributor_dashboard'))
        self.assertNotContains(response, '<span>Masters</span>')

class FormValidationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(username='admin', password='password', user_type=User.Types.ADMIN)
        self.client.force_login(self.admin)

    def test_password_mismatch(self):
        url = reverse('rm_create')
        data = {
            'username': 'rm_fail',
            'email': 'rm_fail@example.com',
            'name': 'RM Fail',
            'password': 'password123',
            'confirm_password': 'password456', # Mismatch
            'employee_code': 'EMP000'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)

        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn("passwords do not match", form.non_field_errors())

    def test_required_fields(self):
        url = reverse('distributor_create')
        data = {
            'username': 'dist_fail',
            # Missing fields
        }
        response = self.client.post(url, data)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        # name is not required by default model field, checking arn_number
        self.assertTrue(form.errors['arn_number'])
