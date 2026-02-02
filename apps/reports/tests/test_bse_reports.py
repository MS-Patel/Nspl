from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.users.models import User, InvestorProfile
from apps.products.models import Scheme, AMC, SchemeCategory
from apps.investments.models import Order
from apps.reconciliation.models import Transaction
import datetime

class BSEReportViewsTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(username='testuser', password='password', user_type=User.Types.INVESTOR)
        self.investor = InvestorProfile.objects.create(user=self.user, pan='ABCDE1234F', ucc_code='TESTUCC')
        self.client.login(username='testuser', password='password')

        # Products
        self.amc = AMC.objects.create(name='Test AMC', code='TAMC')
        self.category = SchemeCategory.objects.create(name='Equity', code='EQ')
        self.scheme = Scheme.objects.create(
            amc=self.amc,
            category=self.category,
            name='Test Scheme',
            scheme_code='SCHEME1',
            isin='INF123456789'
        )

    def test_order_status_report(self):
        # Create Order
        Order.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            amount=1000,
            status=Order.APPROVED,
            bse_order_id='12345',
            bse_remarks='Success',
            unique_ref_no='REF123'
        )

        # Request
        url = reverse('reports:order_status_report')
        today = datetime.date.today().strftime('%d/%m/%Y')
        response = self.client.get(url, {'from_date': today, 'to_date': today})

        # Verify
        self.assertEqual(response.status_code, 200)
        self.assertIn('grid_data_json', response.context)
        self.assertIn('12345', response.context['grid_data_json'])
        self.assertIn('Approved', response.context['grid_data_json'])

    def test_allotment_report(self):
        # Create Transaction
        Transaction.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            folio_number='FOLIO1',
            units=10.5,
            amount=1000,
            nav=100,
            date=datetime.date.today(),
            txn_type_code='P',
            source=Transaction.SOURCE_BSE,
            bse_order_id='54321',
            txn_number='54321'
        )

        url = reverse('reports:allotment_report')
        today = datetime.date.today().strftime('%d/%m/%Y')
        response = self.client.get(url, {'from_date': today, 'to_date': today})

        self.assertEqual(response.status_code, 200)
        self.assertIn('54321', response.context['grid_data_json'])
        self.assertIn('FOLIO1', response.context['grid_data_json'])

    def test_redemption_report(self):
        # Create Transaction
        Transaction.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            folio_number='FOLIO2',
            units=50,
            amount=5000,
            nav=100,
            date=datetime.date.today(),
            txn_type_code='R',
            source=Transaction.SOURCE_BSE,
            bse_order_id='98765',
            txn_number='98765'
        )

        url = reverse('reports:redemption_report')
        today = datetime.date.today().strftime('%d/%m/%Y')
        response = self.client.get(url, {'from_date': today, 'to_date': today})

        self.assertEqual(response.status_code, 200)
        self.assertIn('98765', response.context['grid_data_json'])
        self.assertIn('FOLIO2', response.context['grid_data_json'])
