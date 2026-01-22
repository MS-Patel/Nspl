import pytest
from apps.investments.models import Order, SIP
from apps.users.models import DistributorProfile, InvestorProfile, User
from apps.products.models import Scheme, AMC
from apps.investments.constants import COMPANY_DEFAULT_EUIN
from apps.investments.utils import generate_distributor_based_ref
from django.utils import timezone
import time
from decimal import Decimal

@pytest.mark.django_db
class TestRefAndEUIN:
    def setup_method(self):
        # Create common dependencies
        self.user = User.objects.create(username="testinv", user_type="INVESTOR")
        self.dist_user = User.objects.create(username="testdist", user_type="DISTRIBUTOR")

        self.distributor = DistributorProfile.objects.create(
            user=self.dist_user,
            arn_number="ARN-11111",
            euin="E111111"
        )

        self.distributor_no_euin = DistributorProfile.objects.create(
            user=User.objects.create(username="testdist2", user_type="DISTRIBUTOR"),
            arn_number="ARN-22222",
            euin="" # No EUIN
        )

        self.investor = InvestorProfile.objects.create(
            user=self.user,
            pan="ABCDE1234F",
            distributor=self.distributor
        )

        self.amc = AMC.objects.create(name="Test AMC")
        self.scheme = Scheme.objects.create(amc=self.amc, name="Test Scheme", scheme_code="TEST01")

        # Create a dummy mandate for SIP
        from apps.investments.models import Mandate
        self.mandate = Mandate.objects.create(
            investor=self.investor,
            mandate_id="UMRN001",
            amount_limit=100000,
            start_date=timezone.now().date()
        )

    def test_ref_generation_format(self):
        # Test basic format
        ref = generate_distributor_based_ref(123)
        assert len(ref) == 19
        assert ref.startswith("000123")
        assert ref[6:].isdigit()

    def test_order_ref_and_euin_with_distributor_euin(self):
        order = Order.objects.create(
            investor=self.investor,
            distributor=self.distributor,
            scheme=self.scheme,
            amount=5000
        )

        # Verify Ref No
        assert len(order.unique_ref_no) == 19
        expected_prefix = f"{self.distributor.id:06d}"
        assert order.unique_ref_no.startswith(expected_prefix)

        # Verify EUIN
        assert order.euin == "E111111"

    def test_order_ref_and_euin_fallback(self):
        order = Order.objects.create(
            investor=self.investor,
            distributor=self.distributor_no_euin,
            scheme=self.scheme,
            amount=5000
        )

        # Verify Ref No
        expected_prefix = f"{self.distributor_no_euin.id:06d}"
        assert order.unique_ref_no.startswith(expected_prefix)

        # Verify EUIN Fallback
        assert order.euin == COMPANY_DEFAULT_EUIN

    def test_order_direct_no_distributor(self):
        order = Order.objects.create(
            investor=self.investor,
            distributor=None,
            scheme=self.scheme,
            amount=5000
        )

        # Verify Ref No (Dist ID 0)
        assert order.unique_ref_no.startswith("000000")

        # Verify EUIN Fallback
        assert order.euin == COMPANY_DEFAULT_EUIN

    def test_sip_ref_and_euin(self):
        # Investor has distributor with EUIN
        sip = SIP.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            mandate=self.mandate,
            amount=1000,
            installments=12,
            start_date=timezone.now().date()
        )

        # Verify Ref No
        assert len(sip.unique_ref_no) == 19
        expected_prefix = f"{self.distributor.id:06d}"
        assert sip.unique_ref_no.startswith(expected_prefix)

        # Verify EUIN
        assert sip.euin == "E111111"

    def test_sip_ref_and_euin_fallback(self):
        # Change investor to distributor without EUIN
        self.investor.distributor = self.distributor_no_euin
        self.investor.save()

        sip = SIP.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            mandate=self.mandate,
            amount=1000,
            installments=12,
            start_date=timezone.now().date()
        )

        # Verify Ref No
        expected_prefix = f"{self.distributor_no_euin.id:06d}"
        assert sip.unique_ref_no.startswith(expected_prefix)

        # Verify EUIN
        assert sip.euin == COMPANY_DEFAULT_EUIN
