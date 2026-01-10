import factory
from django.contrib.auth import get_user_model
from apps.users.models import RMProfile, DistributorProfile, InvestorProfile, BankAccount

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('username',)

    username = factory.Faker('user_name')
    email = factory.Faker('email')
    name = factory.Faker('name')
    user_type = User.Types.INVESTOR # Default

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        password = extracted or "password123"
        self.set_password(password)

class RMUserFactory(UserFactory):
    user_type = User.Types.RM

class DistributorUserFactory(UserFactory):
    user_type = User.Types.DISTRIBUTOR

class InvestorUserFactory(UserFactory):
    user_type = User.Types.INVESTOR

class RMProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RMProfile

    user = factory.SubFactory(RMUserFactory)
    employee_code = factory.Sequence(lambda n: f'EMP{n:03d}')

class DistributorProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DistributorProfile

    user = factory.SubFactory(DistributorUserFactory)
    rm = factory.SubFactory(RMProfileFactory)
    arn_number = factory.Sequence(lambda n: f'ARN-{n:05d}')
    mobile = factory.Faker('numerify', text='##########')

class InvestorProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InvestorProfile
        django_get_or_create = ('pan',)

    user = factory.SubFactory(InvestorUserFactory)
    distributor = factory.SubFactory(DistributorProfileFactory)
    pan = factory.Faker('bothify', text='?????####?')
    mobile = factory.Faker('numerify', text='##########')
    dob = factory.Faker('date_of_birth')

class BankAccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BankAccount

    investor = factory.SubFactory(InvestorProfileFactory)
    account_number = factory.Faker('iban')
    ifsc_code = factory.Faker('bothify', text='????0######')
    bank_name = factory.Faker('company')
    branch_name = factory.Faker('city')
