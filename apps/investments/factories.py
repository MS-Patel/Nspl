import factory
from apps.investments.models import Order, Folio, SIP, Mandate
from apps.users.factories import InvestorProfileFactory, DistributorProfileFactory
from apps.products.factories import SchemeFactory, AMCFactory

class MandateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Mandate
        django_get_or_create = ('mandate_id',)

    investor = factory.SubFactory(InvestorProfileFactory)
    mandate_id = factory.Sequence(lambda n: f'UMRN{n:08d}')
    amount_limit = 100000
    start_date = factory.Faker('date_this_year')
    status = Mandate.APPROVED

class FolioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Folio
        django_get_or_create = ('folio_number', 'amc')

    investor = factory.SubFactory(InvestorProfileFactory)
    amc = factory.SubFactory(AMCFactory)
    folio_number = factory.Faker('numerify', text='FOLIO#######')

class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order

    investor = factory.SubFactory(InvestorProfileFactory)
    # Ensure distributor matches investor's distributor usually, but flexible here
    distributor = factory.LazyAttribute(lambda o: o.investor.distributor)
    scheme = factory.SubFactory(SchemeFactory)
    amount = 5000
    status = Order.PENDING
    unique_ref_no = factory.Faker('uuid4')

class SIPFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SIP

    investor = factory.SubFactory(InvestorProfileFactory)
    scheme = factory.SubFactory(SchemeFactory)
    mandate = factory.SubFactory(MandateFactory, investor=factory.SelfAttribute('..investor'))
    amount = 2000
    start_date = factory.Faker('date_this_year')
    installments = 12
