from django.test import TestCase
from apps.integration.utils import get_bse_switch_order_params
from apps.investments.models import Order, Scheme, Folio
from apps.users.models import InvestorProfile
from apps.products.models import AMC
from django.contrib.auth import get_user_model
from unittest.mock import MagicMock
import datetime

class BSESwitchOrderParamsTests(TestCase):
    def test_switch_order_params_structure(self):
        # Mock objects
        User = get_user_model()
        user = User.objects.create(username='testinv')
        investor = InvestorProfile.objects.create(user=user, pan='ABCDE1234F', ucc_code='TEST001')

        amc = AMC.objects.create(name='Test AMC', code='AMC001')

        scheme_source = Scheme.objects.create(name='Source Scheme', scheme_code='SRC001', amc=amc)
        scheme_target = Scheme.objects.create(name='Target Scheme', scheme_code='TGT001', amc=amc)

        folio = Folio.objects.create(investor=investor, amc=amc, folio_number='12345/67')

        order = Order.objects.create(
            investor=investor,
            scheme=scheme_source,
            target_scheme=scheme_target,
            folio=folio,
            transaction_type=Order.SWITCH,
            amount=5000,
            units=0,
            all_redeem=False,
            unique_ref_no='123456'
        )

        params = get_bse_switch_order_params(
            order,
            member_id='MEMBER1',
            user_id='USER1',
            password='enc_password',
            pass_key='pass_key'
        )

        # Verify DPTxn key exists and is 'P'
        self.assertIn('DPTxn', params)
        self.assertEqual(params['DPTxn'], 'P')

        # Verify other fields
        self.assertEqual(params['SwitchCode'], 'SRC001')
        self.assertEqual(params['ToSchemeCode'], 'TGT001')
        self.assertEqual(params['SwitchAmount'], '5000.00')
        self.assertEqual(params['SwitchUnits'], '0')
        self.assertEqual(params['FolioNo'], '12345/67')
        self.assertEqual(params['ClientCode'], 'TEST001')

    def test_switch_all_units(self):
        User = get_user_model()
        user = User.objects.create(username='testinv2')
        investor = InvestorProfile.objects.create(user=user, pan='ABCDE1234G')

        amc = AMC.objects.create(name='Test AMC 2', code='AMC002')

        scheme_source = Scheme.objects.create(name='Source Scheme', scheme_code='SRC002', amc=amc)
        scheme_target = Scheme.objects.create(name='Target Scheme', scheme_code='TGT002', amc=amc)

        order = Order.objects.create(
            investor=investor,
            scheme=scheme_source,
            target_scheme=scheme_target,
            transaction_type=Order.SWITCH,
            amount=0,
            units=0,
            all_redeem=True,
            unique_ref_no='654321'
        )

        params = get_bse_switch_order_params(
            order,
            member_id='MEMBER1',
            user_id='USER1',
            password='enc_password',
            pass_key='pass_key'
        )

        self.assertEqual(params['AllUnitsFlag'], 'Y')
        self.assertEqual(params['SwitchAmount'], '0')
        self.assertEqual(params['SwitchUnits'], '0')
