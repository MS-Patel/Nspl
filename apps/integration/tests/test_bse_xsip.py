import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.users.models import InvestorProfile
from apps.products.models import Scheme
from apps.investments.models import SIP, Folio, Mandate
from apps.integration.utils import get_bse_xsip_order_params

User = get_user_model()

class BSEXsipParamTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testinv', email='test@example.com')
        self.investor = InvestorProfile.objects.create(
            user=self.user,
            pan='ABCDE1234F',
            tax_status=InvestorProfile.INDIVIDUAL
        )
        self.scheme = Scheme.objects.create(
            scheme_code='SCHEME1',
            isin='INF123456789',
            name='Test Scheme'
        )
        self.mandate = Mandate.objects.create(
            investor=self.investor,
            mandate_id='123456',
            amount_limit=10000,
            start_date=datetime.date.today()
        )

    def test_daily_sip_end_date_mapping(self):
        sip = SIP.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            mandate=self.mandate,
            amount=500,
            frequency=SIP.DAILY,
            start_date=datetime.date(2025, 1, 1),
            installments=10,
            unique_ref_no='SIP123'
        )
        params = get_bse_xsip_order_params(sip, "MEMBER", "USER", "PASS", "KEY")
        # 10 days from 2025-01-01 is 2025-01-11
        self.assertEqual(params['Param3'], '11/01/2025')
        self.assertEqual(params['FrequencyType'], 'DAILY')

    def test_daily_sip_perpetual(self):
        sip = SIP.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            mandate=self.mandate,
            amount=500,
            frequency=SIP.DAILY,
            start_date=datetime.date(2025, 1, 1),
            unique_ref_no='SIP124'
        )
        params = get_bse_xsip_order_params(sip, "MEMBER", "USER", "PASS", "KEY")
        self.assertEqual(params['Param3'], '31/12/2099')

    def test_daily_sip_with_explicit_end_date(self):
        sip = SIP.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            mandate=self.mandate,
            amount=500,
            frequency=SIP.DAILY,
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 12, 31),
            unique_ref_no='SIP125'
        )
        params = get_bse_xsip_order_params(sip, "MEMBER", "USER", "PASS", "KEY")
        self.assertEqual(params['Param3'], '31/12/2025')

    def test_monthly_sip_no_param3(self):
        sip = SIP.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            mandate=self.mandate,
            amount=500,
            frequency=SIP.MONTHLY,
            start_date=datetime.date(2025, 1, 1),
            installments=12,
            unique_ref_no='SIP126'
        )
        params = get_bse_xsip_order_params(sip, "MEMBER", "USER", "PASS", "KEY")
        self.assertEqual(params['Param3'], '')
