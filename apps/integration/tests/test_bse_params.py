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
            holding_nature=InvestorProfile.SINGLE,
            nomination_opt='Y',
            nomination_auth_mode='O'
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

        # Bank Details start at Index 41 (Field 42)
        # 41: Acc Type, 42: Acc No, 43: MICR, 44: IFSC, 45: Default
        self.assertEqual(fields[41], 'SB') # Bank 1 Type
        self.assertEqual(fields[42], '1234567890') # Bank 1 Acc No
        self.assertEqual(fields[44], 'HDFC0000123') # Bank 1 IFSC

    def test_full_details_param_string(self):
        # Add Foreign Addr
        self.investor.foreign_address_1 = '123 Main St'
        self.investor.foreign_city = 'New York'
        self.investor.foreign_country = 'USA'

        # Add Joint Holder
        self.investor.second_applicant_name = 'Jane Doe'
        self.investor.second_applicant_dob = datetime.date(1992, 2, 2)

        # Add Nominee with Aadhaar
        nominee = Nominee.objects.create(
            investor=self.investor,
            name='Baby Doe',
            relationship='Son',
            percentage=100,
            address_1='Nom Addr 1',
            city='Pune',
            mobile='9999999999',
            id_type='G', # Aadhaar
            id_number='123456789012'
        )

        self.investor.save()

        param_str = map_investor_to_bse_param_string(self.investor)
        fields = param_str.split('|')
        self.assertEqual(len(fields), 183)

        # Check Joint Holder (Index 9)
        # f01_09 (0-8) -> f10_21 (9-20)
        self.assertEqual(fields[9], 'Jane')
        self.assertEqual(fields[15], '02/02/1992')

        # Check Foreign Addr
        # f82_92 starts at Index 81
        self.assertEqual(fields[81], '123 Main St')
        self.assertEqual(fields[84], 'New York')

        # Check Nominee (Starts at Index 123)
        # 121: Nom Opt (f121_123 starts at 120. 120=Guard Rel, 121=Opt, 122=Auth)
        self.assertEqual(fields[121], 'Y')

        # Nominee 1 Details (Index 123)
        self.assertEqual(fields[123], 'Baby Doe')
        self.assertEqual(fields[124], '18') # Son -> 18

        # ID Type (130) and ID Number (131)
        self.assertEqual(fields[130], '2') # Aadhaar -> 2
        self.assertEqual(fields[131], '9012') # Last 4 digits

        # Address 1 (Index 134)
        self.assertEqual(fields[134], 'Nom Addr 1')
        # City (Index 137)
        self.assertEqual(fields[137], 'Pune')

    def test_relationship_mapping(self):
        # Verify specific relationship codes
        from apps.integration.utils import get_rel_code
        self.assertEqual(get_rel_code("Brother"), '03')
        self.assertEqual(get_rel_code("Brother-in-law"), '02')
        self.assertEqual(get_rel_code("Spouse"), '20')
        self.assertEqual(get_rel_code("Wife"), '20')
        self.assertEqual(get_rel_code("Father"), '06')
        self.assertEqual(get_rel_code("Father-in-law"), '07')
        self.assertEqual(get_rel_code("Unknown"), '22')
