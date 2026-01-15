import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.users.models import InvestorProfile, BankAccount, Nominee
from apps.integration.utils import map_investor_to_bse_param_string

User = get_user_model()

class BSEParamStringTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testinv', email='test@example.com', first_name='John', last_name='Doe')
        self.investor = InvestorProfile.objects.create(
            user=self.user,
            pan='ABCDE1234F',
            dob=datetime.date(1990, 1, 1),
            gender='M',
            mobile='9876543210',
            address_1='Flat 101',
            address_2='Residency',
            city='Mumbai',
            state='MAHARASHTRA',
            pincode='400001',
            tax_status=InvestorProfile.INDIVIDUAL,
            client_type=InvestorProfile.PHYSICAL,
            holding_nature=InvestorProfile.SINGLE
        )
        self.bank = BankAccount.objects.create(
            investor=self.investor,
            ifsc_code='HDFC0000123',
            account_number='1234567890',
            account_type='SB',
            is_default=True
        )

    def test_basic_param_string(self):
        param_str = map_investor_to_bse_param_string(self.investor)
        fields = param_str.split('|')
        self.assertEqual(len(fields), 183)
        self.assertEqual(fields[0], 'ABCDE1234F') # Client Code
        self.assertEqual(fields[1], 'John') # First Name
        self.assertEqual(fields[40], 'SB') # Bank 1 Type
        self.assertEqual(fields[41], '1234567890') # Bank 1 Acc No

    def test_full_details_param_string(self):
        # Add Foreign Addr
        self.investor.foreign_address_1 = '123 Main St'
        self.investor.foreign_city = 'New York'
        self.investor.foreign_country = 'USA'

        # Add Joint Holder
        self.investor.second_applicant_name = 'Jane Doe'
        self.investor.second_applicant_dob = datetime.date(1992, 2, 2)

        # Add Nominee
        nominee = Nominee.objects.create(
            investor=self.investor,
            name='Baby Doe',
            relationship='Son',
            percentage=100,
            address_1='Nom Addr 1',
            city='Pune',
            mobile='9999999999'
        )

        self.investor.save()

        param_str = map_investor_to_bse_param_string(self.investor)
        fields = param_str.split('|')
        self.assertEqual(len(fields), 183)

        # Check Joint Holder (Index 9)
        self.assertEqual(fields[9], 'Jane')
        self.assertEqual(fields[15], '02/02/1992')

        # Check Foreign Addr (Index 80)
        self.assertEqual(fields[80], '123 Main St')
        self.assertEqual(fields[83], 'New York')

        # Check Nominee (Index 122 start)
        # 120: Y
        self.assertEqual(fields[120], 'Y')
        # 122: Name
        self.assertEqual(fields[122], 'Baby Doe')
        # 131: Nom Addr 1 (122+9) -> 131
        self.assertEqual(fields[131], 'Nom Addr 1')
        # 134: Nom City (122+12)
        self.assertEqual(fields[134], 'Pune')
