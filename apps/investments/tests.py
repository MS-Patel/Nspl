from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.users.models import InvestorProfile, DistributorProfile
from apps.products.models import Scheme, AMC
from .models import Order, Folio

User = get_user_model()

class OrderModelTest(TestCase):
    def setUp(self):
        # Create Users
        self.distributor_user = User.objects.create_user(username='dist1', password='password', user_type=User.Types.DISTRIBUTOR)
        self.investor_user = User.objects.create_user(username='inv1', password='password', user_type=User.Types.INVESTOR)

        # Create Profiles
        self.distributor_profile = DistributorProfile.objects.create(user=self.distributor_user, arn_number='12345', euin='E12345')
        self.investor_profile = InvestorProfile.objects.create(user=self.investor_user, distributor=self.distributor_profile, pan='ABCDE1234F')

        # Create Product Data
        self.amc = AMC.objects.create(name='Test AMC', code='AMC01')
        self.scheme = Scheme.objects.create(
            amc=self.amc,
            name='Test Scheme',
            scheme_code='SCH01',
            min_purchase_amount=1000,
            isin='INE123456789'
        )

    def test_order_creation_lumpsum(self):
        order = Order.objects.create(
            investor=self.investor_profile,
            scheme=self.scheme,
            amount=5000,
            payment_mode=Order.DIRECT,
            is_new_folio=True
        )
        self.assertEqual(order.status, Order.PENDING)
        self.assertEqual(order.amount, 5000)
        self.assertTrue(order.unique_ref_no)

    def test_order_euin_autofill(self):
        # Distributor has EUIN 'E12345', should be copied to Order on save
        order = Order.objects.create(
            investor=self.investor_profile, # This investor is linked to self.distributor_profile
            distributor=self.distributor_profile,
            scheme=self.scheme,
            amount=2000
        )
        self.assertEqual(order.euin, 'E12345')

    def test_folio_linkage(self):
        folio = Folio.objects.create(investor=self.investor_profile, amc=self.amc, folio_number='10101010')
        order = Order.objects.create(
            investor=self.investor_profile,
            scheme=self.scheme,
            amount=5000,
            folio=folio
        )
        self.assertEqual(order.folio, folio)
        self.assertFalse(order.is_new_folio)

