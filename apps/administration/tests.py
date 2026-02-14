from django.test import TestCase
from django.core.cache import cache
from apps.administration.models import SystemConfiguration
from apps.integration.utils import get_bse_order_params, get_bse_xsip_order_params, get_bse_switch_order_params
from unittest.mock import MagicMock
from decimal import Decimal
import datetime
from django.db import transaction, IntegrityError

class SystemConfigurationTest(TestCase):
    def setUp(self):
        cache.clear()
        self.config = SystemConfiguration.get_solo()
        self.config.default_euin = "E123456"
        self.config.save()

    def test_singleton(self):
        """Test that only one instance is created."""
        # Trying to create another one should fail because save() enforces pk=1 and create() forces insert
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SystemConfiguration.objects.create(default_euin="E999999")

        # Proper way to update
        config = SystemConfiguration.get_solo()
        config.default_euin = "E999999"
        config.save()

        config3 = SystemConfiguration.objects.get(pk=1)
        self.assertEqual(config3.default_euin, "E999999")

    def test_euin_fallback_order(self):
        """Test that get_bse_order_params falls back to default EUIN."""
        order = MagicMock()
        order.transaction_type = "PURCHASE"
        order.is_new_folio = True
        order.investor.ucc_code = "UCC123"
        order.euin = "" # Empty
        order.folio.folio_number = "123"
        order.amount = Decimal("1000.00")
        order.units = Decimal("0")
        order.all_redeem = False
        order.scheme.scheme_code = "SCHEME1"
        order.investor.mobile = "9999999999"
        order.investor.email = "test@example.com"
        order.mandate = None

        params = get_bse_order_params(order, "MEMBER", "USER", "PASS", "KEY")
        self.assertEqual(params['EUIN'], "E123456")
        self.assertEqual(params['EUINVal'], "Y")

        # Test with explicit EUIN
        order.euin = "E888888"
        params = get_bse_order_params(order, "MEMBER", "USER", "PASS", "KEY")
        self.assertEqual(params['EUIN'], "E888888")

    def test_euin_fallback_xsip(self):
        """Test that get_bse_xsip_order_params falls back to default EUIN."""
        sip = MagicMock()
        sip.unique_ref_no = "REF123"
        sip.scheme.scheme_code = "SCHEME1"
        sip.investor.ucc_code = "UCC123"
        sip.euin = ""
        sip.folio.folio_number = "123"
        sip.start_date = datetime.date.today()
        sip.frequency = "MONTHLY"
        sip.amount = Decimal("1000.00")
        sip.installments = 12
        sip.mandate.mandate_id = "MANDATE1"

        params = get_bse_xsip_order_params(sip, "MEMBER", "USER", "PASS", "KEY")
        self.assertEqual(params['Euin'], "E123456")
        self.assertEqual(params['EuinVal'], "Y")

    def test_euin_fallback_switch(self):
        """Test that get_bse_switch_order_params falls back to default EUIN."""
        order = MagicMock()
        order.unique_ref_no = "REF123"
        order.investor.ucc_code = "UCC123"
        order.euin = ""
        order.folio.folio_number = "123"
        order.scheme.scheme_code = "SOURCE"
        order.target_scheme.scheme_code = "TARGET"
        order.all_redeem = False
        order.amount = Decimal("1000.00")
        order.units = Decimal("0")

        params = get_bse_switch_order_params(order, "MEMBER", "USER", "PASS", "KEY")
        self.assertEqual(params['Euin'], "E123456")
        self.assertEqual(params['EuinVal'], "Y")

    def test_form_validation(self):
        from apps.administration.forms import SystemConfigurationForm
        form = SystemConfigurationForm(data={
            'company_name': 'Test Company',
            'email_host': 'smtp.test.com',
            'email_port': 587,
            'default_from_email': 'test@test.com'
        })
        self.assertTrue(form.is_valid())
