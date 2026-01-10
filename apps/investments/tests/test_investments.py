import pytest
from apps.investments.models import Order, SIP, Mandate
from apps.investments.factories import OrderFactory, SIPFactory, MandateFactory, FolioFactory
from apps.users.factories import DistributorProfileFactory

@pytest.mark.django_db
class TestOrderModel:
    def test_order_creation(self):
        order = OrderFactory()
        assert order.unique_ref_no is not None
        assert order.status == Order.PENDING

    def test_euin_autofill(self):
        # Create a distributor with a specific EUIN
        dist = DistributorProfileFactory(euin="EUIN123456")
        # Create an order linked to this distributor, but don't set EUIN on order explicitly
        order = OrderFactory(distributor=dist, euin="")

        # Saving happens in factory, but let's re-save or check if factory triggered save() logic
        # Factory calls save(), so the model's save() method should have run.
        assert order.euin == "EUIN123456"

    def test_order_relationships(self):
        folio = FolioFactory()
        order = OrderFactory(investor=folio.investor, folio=folio, scheme=folio.amc.schemes.create(scheme_code="TESTSCH", name="Test"))
        assert order.folio == folio
        assert order.investor == folio.investor

@pytest.mark.django_db
class TestSIPModel:
    def test_sip_creation(self):
        sip = SIPFactory()
        assert sip.status == SIP.STATUS_PENDING
        assert sip.installments == 12
        assert sip.mandate.investor == sip.investor

@pytest.mark.django_db
class TestMandateModel:
    def test_mandate_creation(self):
        mandate = MandateFactory()
        assert mandate.status == Mandate.APPROVED
