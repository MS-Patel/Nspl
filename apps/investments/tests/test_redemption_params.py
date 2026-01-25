from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.users.models import InvestorProfile, DistributorProfile
from apps.products.models import Scheme, AMC, SchemeCategory
from apps.investments.models import Order, Folio
from apps.integration.utils import get_bse_order_params
from decimal import Decimal
import datetime

User = get_user_model()

class RedemptionParamsTest(TestCase):
    def setUp(self):
        # Setup Data
        self.user = User.objects.create_user(username='testinv', email='test@example.com', first_name='John', last_name='Doe')
        self.investor = InvestorProfile.objects.create(
            user=self.user, pan='ABCDE1234F', mobile='9876543210', email='test@example.com'
        )
        self.distributor_user = User.objects.create_user(username='testdist', user_type='DISTRIBUTOR')
        self.distributor = DistributorProfile.objects.create(user=self.distributor_user, arn_number='ARN-12345')

        self.amc = AMC.objects.create(name='Test AMC', code='101')
        self.cat = SchemeCategory.objects.create(name='Equity')
        self.scheme = Scheme.objects.create(
            amc=self.amc, category=self.cat, name='Test Scheme', scheme_code='TEST001',
            isin='INE123456789'
        )
        self.folio = Folio.objects.create(
            investor=self.investor, amc=self.amc, folio_number='1234567/89'
        )

    def test_redemption_by_amount(self):
        order = Order.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            folio=self.folio,
            transaction_type=Order.REDEMPTION,
            amount=5000,
            units=0,
            all_redeem=False
        )

        params = get_bse_order_params(order, 'MEMBER', 'USER', 'PASS', 'KEY')

        self.assertEqual(params['BuySell'], 'R')
        self.assertEqual(params['AllRedeem'], 'N')
        self.assertEqual(params['OrderVal'], '5000.00')
        self.assertEqual(params['Qty'], '0')

    def test_redemption_by_units(self):
        order = Order.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            folio=self.folio,
            transaction_type=Order.REDEMPTION,
            amount=0,
            units=Decimal('10.500'),
            all_redeem=False
        )

        params = get_bse_order_params(order, 'MEMBER', 'USER', 'PASS', 'KEY')

        self.assertEqual(params['BuySell'], 'R')
        self.assertEqual(params['AllRedeem'], 'N')
        self.assertEqual(params['Qty'], '10.5000')
        self.assertEqual(params['OrderVal'], '0')

    def test_redemption_all(self):
        order = Order.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            folio=self.folio,
            transaction_type=Order.REDEMPTION,
            amount=0,
            units=0,
            all_redeem=True
        )

        params = get_bse_order_params(order, 'MEMBER', 'USER', 'PASS', 'KEY')

        self.assertEqual(params['BuySell'], 'R')
        self.assertEqual(params['AllRedeem'], 'Y')
        # BSE might ignore Qty/OrderVal, but we verify they are defaulted
        self.assertEqual(params['Qty'], '0')
        self.assertEqual(params['OrderVal'], '0')
