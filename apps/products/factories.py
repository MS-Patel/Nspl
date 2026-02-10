import factory
from apps.products.models import AMC, Scheme, SchemeCategory, NAVHistory

class AMCFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AMC
        django_get_or_create = ('code',)

    name = factory.Faker('company')
    code = factory.Sequence(lambda n: f'AMC{n:03d}')

class SchemeCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SchemeCategory
        django_get_or_create = ('code',)

    name = factory.Faker('bs')
    code = factory.Sequence(lambda n: f'CAT{n:03d}')

class SchemeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Scheme
        django_get_or_create = ('scheme_code',)

    amc = factory.SubFactory(AMCFactory)
    category = factory.SubFactory(SchemeCategoryFactory)
    name = factory.Faker('catch_phrase')
    isin = factory.Faker('bothify', text='IN##########')
    scheme_code = factory.Sequence(lambda n: f'SCH{n:05d}')

    purchase_allowed = True
    min_purchase_amount = 5000

    redemption_allowed = True

class NAVHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NAVHistory
        django_get_or_create = ('scheme', 'nav_date')

    scheme = factory.SubFactory(SchemeFactory)
    nav_date = factory.Faker('date_this_year')
    net_asset_value = factory.Faker('pydecimal', left_digits=4, right_digits=4, positive=True)
