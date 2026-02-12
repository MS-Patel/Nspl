from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    class Types(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        RM = 'RM', 'Relationship Manager'
        DISTRIBUTOR = 'DISTRIBUTOR', 'Distributor'
        INVESTOR = 'INVESTOR', 'Investor'

    user_type = models.CharField(
        _('Type'), max_length=50, choices=Types.choices, default=Types.ADMIN
    )

    name = models.CharField(_("Name of User"), blank=True, max_length=255)

    def save(self, *args, **kwargs):
        if not self.id:
            # If creating a superuser via CLI, ensure they are ADMIN
            if self.is_superuser:
                self.user_type = self.Types.ADMIN
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"/users/{self.username}/"

class Branch(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=50, blank=True)
    state = models.CharField(max_length=50, blank=True)
    pincode = models.CharField(max_length=6, blank=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name_plural = "Branches"

class RMProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='rm_profile')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='rms')
    employee_code = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"{self.user.username} (RM)"

class DistributorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='distributor_profile')
    rm = models.ForeignKey(RMProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='distributors')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_distributors')

    arn_number = models.CharField(max_length=50, unique=True, help_text="AMFI Registration Number")
    euin = models.CharField(max_length=50, blank=True, help_text="Employee Unique Identification Number")
    pan = models.CharField(max_length=10, blank=True)
    mobile = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return f"{self.user.username} (ARN-{self.arn_number})"

class InvestorProfile(models.Model):
    # Tax Status Choices
    INDIVIDUAL = '01'
    MINOR = '02'
    HUF = '03'
    COMPANY = '04'
    NRI_REPATRIABLE = '21'
    NRI_NON_REPATRIABLE = '24'

    TAX_STATUS_CHOICES = [
        (INDIVIDUAL, 'Individual'),
        (MINOR, 'On Behalf of Minor'),
        (HUF, 'HUF'),
        (COMPANY, 'Company'),
        (NRI_REPATRIABLE, 'NRI (Repatriable)'),
        (NRI_NON_REPATRIABLE, 'NRI (Non-Repatriable)'),
    ]

    # Occupation Choices
    BUSINESS = '01'
    SERVICE = '02'
    PROFESSIONAL = '03'
    AGRICULTURIST = '04'
    RETIRED = '05'
    HOUSEWIFE = '06'
    STUDENT = '07'
    OTHERS = '08'

    OCCUPATION_CHOICES = [
        (BUSINESS, 'Business'),
        (SERVICE, 'Service'),
        (PROFESSIONAL, 'Professional'),
        (AGRICULTURIST, 'Agriculturist'),
        (RETIRED, 'Retired'),
        (HOUSEWIFE, 'Housewife'),
        (STUDENT, 'Student'),
        (OTHERS, 'Others'),
    ]

    # Holding Nature
    SINGLE = 'SI'
    JOINT = 'JO'
    ANYONE_SURVIVOR = 'AS'

    HOLDING_CHOICES = [
        (SINGLE, 'Single'),
        (JOINT, 'Joint'),
        (ANYONE_SURVIVOR, 'Anyone or Survivor'),
    ]

    # Client Type / Mode
    PHYSICAL = 'P'
    DEMAT = 'D'
    CLIENT_TYPE_CHOICES = [
        (PHYSICAL, 'Physical'),
        (DEMAT, 'Demat'),
    ]

    # Depository
    CDSL = 'C'
    NSDL = 'N'
    DEPOSITORY_CHOICES = [
        (CDSL, 'CDSL'),
        (NSDL, 'NSDL'),
    ]

    # KYC Types
    KRA_COMPLIANT = 'K'
    CKYC_COMPLIANT = 'C'
    BIOMETRIC = 'B'
    AADHAAR_EKYC = 'E'

    KYC_TYPE_CHOICES = [
        (KRA_COMPLIANT, 'KRA Compliant'),
        (CKYC_COMPLIANT, 'CKYC Compliant'),
        (BIOMETRIC, 'Biometric KYC'),
        (AADHAAR_EKYC, 'Aadhaar E-KYC'),
    ]

    # Declaration Choices
    SELF = 'SE'
    SPOUSE = 'SP'
    DEPENDENT_CHILDREN = 'DC'
    DEPENDENT_SIBLINGS = 'DS'
    DEPENDENT_PARENTS = 'DP'
    GUARDIAN = 'GD'
    PMS = 'PM'
    CUSTODIAN = 'CD'
    POA = 'PO'

    DECLARATION_CHOICES = [
        (SELF, 'Self'),
        (SPOUSE, 'Spouse'),
        (DEPENDENT_CHILDREN, 'Dependent Children'),
        (DEPENDENT_SIBLINGS, 'Dependent Siblings'),
        (DEPENDENT_PARENTS, 'Dependent Parents'),
        (GUARDIAN, 'Guardian'),
        (PMS, 'PMS'),
        (CUSTODIAN, 'Custodian'),
        (POA, 'POA'),
    ]

    # Nominee Auth Status Choices
    AUTH_AUTHENTICATED = 'A'
    AUTH_PENDING = 'P'
    AUTH_NOT_AVAILABLE = 'N'

    NOMINEE_AUTH_STATUS_CHOICES = [
        (AUTH_AUTHENTICATED, 'Authenticated'),
        (AUTH_PENDING, 'Pending'),
        (AUTH_NOT_AVAILABLE, 'Not Available'),
    ]

    # Source of Wealth Choices
    SALARY = '01'
    BUSINESS_INCOME = '02'
    GIFT = '03'
    ANCESTRAL_PROPERTY = '04'
    RENTAL_INCOME = '05'
    PRIZE_MONEY = '06'
    ROYALTY = '07'
    OTHERS_WEALTH = '08'

    SOURCE_OF_WEALTH_CHOICES = [
        (SALARY, 'Salary'),
        (BUSINESS_INCOME, 'Business Income'),
        (GIFT, 'Gift'),
        (ANCESTRAL_PROPERTY, 'Ancestral Property'),
        (RENTAL_INCOME, 'Rental Income'),
        (PRIZE_MONEY, 'Prize Money'),
        (ROYALTY, 'Royalty'),
        (OTHERS_WEALTH, 'Others'),
    ]

    # Income Slab Choices
    BELOW_1L = '31'
    ONE_TO_5L = '32'
    FIVE_TO_10L = '33'
    TEN_TO_25L = '34'
    TWENTYFIVE_TO_1CR = '35'
    ABOVE_1CR = '36'

    INCOME_SLAB_CHOICES = [
        (BELOW_1L, 'Below 1 Lakh'),
        (ONE_TO_5L, '> 1 <= 5 Lacs'),
        (FIVE_TO_10L, '> 5 <= 10 Lacs'),
        (TEN_TO_25L, '> 10 <= 25 Lacs'),
        (TWENTYFIVE_TO_1CR, '> 25 Lacs <= 1 Crore'),
        (ABOVE_1CR, 'Above 1 Crore'),
    ]

    # PEP Choices
    PEP_YES = 'Y'
    PEP_NO = 'N'
    PEP_RELATIVE = 'R'

    PEP_CHOICES = [
        (PEP_YES, 'Yes'),
        (PEP_NO, 'No'),
        (PEP_RELATIVE, 'Relative'),
    ]

    # Exemption Code Choices
    EXEMPTION_CODE_CHOICES = [
        ('A', 'A - 501(a) Organization'),
        ('B', 'B - US Government'),
        ('C', 'C - State/US Possession'),
        ('D', 'D - Publicly Traded Corp'),
        ('E', 'E - Member of Expanded Affiliated Group'),
        ('F', 'F - Dealer in Securities'),
        ('G', 'G - REIT'),
        ('H', 'H - Regulated Investment Company'),
        ('I', 'I - Common Trust Fund'),
        ('J', 'J - Bank'),
        ('K', 'K - Broker'),
        ('L', 'L - Exempt Trust'),
        ('M', 'M - Tax Exempt Trust 403(b)/457(g)'),
        ('N', 'N - Not Applicable'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='investor_profile')

    # Hierarchy Fields
    distributor = models.ForeignKey(DistributorProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='investors')
    rm = models.ForeignKey(RMProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='investors')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='investors')

    # Basic Info
    firstname = models.CharField(max_length=100, blank=True, default='')
    middlename = models.CharField(max_length=100, blank=True, default='')
    lastname = models.CharField(max_length=100, blank=True, default='')
    pan = models.CharField(max_length=10, unique=True)
    dob = models.DateField(null=True, blank=True, verbose_name="Date of Birth")
    gender = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], blank=True)
    mobile = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)

    # Address Details
    address_1 = models.CharField(max_length=40, blank=True)
    address_2 = models.CharField(max_length=40, blank=True)
    address_3 = models.CharField(max_length=40, blank=True)
    city = models.CharField(max_length=35, blank=True)
    state = models.CharField(max_length=30, blank=True) # Could be a ChoiceField later
    pincode = models.CharField(max_length=6, blank=True)
    country = models.CharField(max_length=35, default='India', blank=True)

    # Foreign Address Details (For NRI)
    foreign_address_1 = models.CharField(max_length=40, blank=True, default='')
    foreign_address_2 = models.CharField(max_length=40, blank=True, default='')
    foreign_address_3 = models.CharField(max_length=40, blank=True, default='')
    foreign_city = models.CharField(max_length=35, blank=True, default='')
    foreign_state = models.CharField(max_length=35, blank=True, default='')
    foreign_pincode = models.CharField(max_length=10, blank=True, default='')
    foreign_country = models.CharField(max_length=35, blank=True, default='')
    foreign_resi_phone = models.CharField(max_length=15, blank=True, default='')
    foreign_res_fax = models.CharField(max_length=15, blank=True, default='')
    foreign_off_phone = models.CharField(max_length=15, blank=True, default='')
    foreign_off_fax = models.CharField(max_length=15, blank=True, default='')

    # BSE Specific Fields
    tax_status = models.CharField(max_length=2, choices=TAX_STATUS_CHOICES, default=INDIVIDUAL)
    occupation = models.CharField(max_length=2, choices=OCCUPATION_CHOICES, default=SERVICE)
    holding_nature = models.CharField(max_length=2, choices=HOLDING_CHOICES, default=SINGLE)

    # FATCA Fields
    place_of_birth = models.CharField(max_length=50, default='India', blank=True)
    country_of_birth = models.CharField(max_length=50, default='India', blank=True)
    source_of_wealth = models.CharField(max_length=2, choices=SOURCE_OF_WEALTH_CHOICES, default=SALARY)
    income_slab = models.CharField(max_length=2, choices=INCOME_SLAB_CHOICES, default=ONE_TO_5L)
    pep_status = models.CharField(max_length=1, choices=PEP_CHOICES, default=PEP_NO)
    exemption_code = models.CharField(max_length=1, choices=EXEMPTION_CODE_CHOICES, blank=True)

    # Demat Details
    client_type = models.CharField(max_length=1, choices=CLIENT_TYPE_CHOICES, default=PHYSICAL, blank=True)
    depository = models.CharField(max_length=1, choices=DEPOSITORY_CHOICES, blank=True)
    dp_id = models.CharField(max_length=20, blank=True, help_text="Depository Participant ID")
    client_id = models.CharField(max_length=20, blank=True, help_text="Beneficiary ID / Client ID")

    # Joint Holders Details
    second_applicant_name = models.CharField(max_length=70, blank=True)
    second_applicant_pan = models.CharField(max_length=10, blank=True)
    second_applicant_dob = models.DateField(null=True, blank=True)
    second_applicant_email = models.EmailField(blank=True)
    second_applicant_mobile = models.CharField(max_length=15, blank=True)
    second_applicant_kyc_type = models.CharField(max_length=1, choices=KYC_TYPE_CHOICES, blank=True)
    second_applicant_ckyc_number = models.CharField(max_length=14, blank=True)
    second_applicant_kra_exempt_ref_no = models.CharField(max_length=10, blank=True)
    second_applicant_email_declaration = models.CharField(max_length=2, choices=DECLARATION_CHOICES, default=SELF, blank=True)
    second_applicant_mobile_declaration = models.CharField(max_length=2, choices=DECLARATION_CHOICES, default=SELF, blank=True)

    third_applicant_name = models.CharField(max_length=70, blank=True)
    third_applicant_pan = models.CharField(max_length=10, blank=True)
    third_applicant_dob = models.DateField(null=True, blank=True)
    third_applicant_email = models.EmailField(blank=True)
    third_applicant_mobile = models.CharField(max_length=15, blank=True)
    third_applicant_kyc_type = models.CharField(max_length=1, choices=KYC_TYPE_CHOICES, blank=True)
    third_applicant_ckyc_number = models.CharField(max_length=14, blank=True)
    third_applicant_kra_exempt_ref_no = models.CharField(max_length=10, blank=True)
    third_applicant_email_declaration = models.CharField(max_length=2, choices=DECLARATION_CHOICES, default=SELF, blank=True)
    third_applicant_mobile_declaration = models.CharField(max_length=2, choices=DECLARATION_CHOICES, default=SELF, blank=True)

    # Guardian Details
    guardian_name = models.CharField(max_length=70, blank=True, help_text="Required if Tax Status is Minor")
    guardian_pan = models.CharField(max_length=10, blank=True, help_text="Required if Tax Status is Minor")
    guardian_kyc_type = models.CharField(max_length=1, choices=KYC_TYPE_CHOICES, blank=True)
    guardian_ckyc_number = models.CharField(max_length=14, blank=True)
    guardian_kra_exempt_ref_no = models.CharField(max_length=10, blank=True)
    guardian_relationship = models.CharField(max_length=50, blank=True) # Could be choice field later

    # Additional BSE 183 Fields
    paperless_flag = models.CharField(max_length=1, default='P', choices=[('P', 'Physical'), ('Z', 'Paperless')], blank=True)
    lei_no = models.CharField(max_length=20, blank=True, default='')
    lei_validity = models.DateField(null=True, blank=True)
    mapin_id = models.CharField(max_length=20, blank=True, default='')

    # New Fields for V183
    kyc_type = models.CharField(max_length=1, choices=KYC_TYPE_CHOICES, default=KRA_COMPLIANT, blank=True)
    ckyc_number = models.CharField(max_length=14, blank=True)
    kra_exempt_ref_no = models.CharField(max_length=10, blank=True)
    mobile_declaration = models.CharField(max_length=2, choices=DECLARATION_CHOICES, default=SELF, blank=True)
    email_declaration = models.CharField(max_length=2, choices=DECLARATION_CHOICES, default=SELF, blank=True)
    nomination_opt = models.CharField(max_length=1, choices=[('Y', 'Yes'), ('N', 'No')], default='N')

    # Updated Auth Mode Choices
    WET_SIGNATURE = 'W'
    ONLINE_OTP = 'O'
    ESIGN = 'E'
    PHYSICAL_LEGACY = 'P' # Keeping P for backward compatibility if needed, but labeled as Wet Signature?
    # Spec says W, E, O.
    # We will encourage W, O, E.
    AUTH_MODE_CHOICES = [
        (WET_SIGNATURE, 'Wet Signature'),
        (ONLINE_OTP, 'Online/OTP'),
        (ESIGN, 'eSign'),
        (PHYSICAL_LEGACY, 'Physical (Legacy)'), # To avoid breaking existing 'P' rows immediately
    ]
    nomination_auth_mode = models.CharField(max_length=1, choices=AUTH_MODE_CHOICES, blank=True, default=WET_SIGNATURE)

    # Status Flags
    kyc_status = models.BooleanField(default=False)
    ucc_code = models.CharField(max_length=20, blank=True, null=True, help_text="Unique Client Code from BSE")

    # BSE Compliance & Audit
    nominee_auth_status = models.CharField(
        max_length=1,
        choices=NOMINEE_AUTH_STATUS_CHOICES,
        default=AUTH_NOT_AVAILABLE,
        help_text="A: Authenticated, P: Pending, N: Not Available"
    )
    last_verified_at = models.DateTimeField(null=True, blank=True)
    bse_remarks = models.TextField(blank=True, help_text="Response remarks from BSE")

    is_offline = models.BooleanField(
        default=False,
        help_text="True if investor is onboarded offline via RTA feed and not yet synced with BSE."
    )

    def __str__(self):
        return f"{self.user.username} (PAN-{self.pan})"

class BankAccount(models.Model):
    ACCOUNT_TYPES = [
        ('SB', 'Savings'),
        ('CB', 'Current'),
        ('NE', 'NRE'),
        ('NO', 'NRO'),
    ]

    investor = models.ForeignKey(InvestorProfile, on_delete=models.CASCADE, related_name='bank_accounts')
    ifsc_code = models.CharField(max_length=11)
    account_number = models.CharField(max_length=20)
    account_type = models.CharField(max_length=2, choices=ACCOUNT_TYPES, default='SB')
    bank_name = models.CharField(max_length=100, blank=True)
    branch_name = models.CharField(max_length=100, blank=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"

class Nominee(models.Model):
    RELATIONSHIP_CHOICES = [
        ('Spouse', 'Spouse'),
        ('Father', 'Father'),
        ('Mother', 'Mother'),
        ('Son', 'Son'),
        ('Daughter', 'Daughter'),
        ('Others', 'Others'),
    ]

    ID_TYPE_CHOICES = [
        ('A', 'Passport'),
        ('B', 'Election ID Card'),
        ('C', 'PAN Card'),
        ('D', 'ID Card'),
        ('E', 'Driving License'),
        ('G', 'UIDIA / Aadhar letter'),
        ('H', 'NREGA Job Card'),
        ('O', 'Others'),
        ('X', 'Not categorized'),
        ('T', 'TIN'),
        ('C1', 'Company Identification Number'),
        ('G1', 'US GIIN'),
        ('E1', 'Global Entity Identification Number'),
    ]

    investor = models.ForeignKey(InvestorProfile, on_delete=models.CASCADE, related_name='nominees')
    name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50, choices=RELATIONSHIP_CHOICES, default='Others')
    percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage of allocation")
    date_of_birth = models.DateField(null=True, blank=True, help_text="Required if nominee is a minor")
    guardian_name = models.CharField(max_length=100, blank=True, help_text="If nominee is a minor")
    guardian_pan = models.CharField(max_length=10, blank=True, help_text="If nominee is a minor")
    pan = models.CharField(max_length=10, blank=True, help_text="Nominee PAN (Optional)")

    # Address & Contact
    address_1 = models.CharField(max_length=40, blank=True, default='')
    address_2 = models.CharField(max_length=40, blank=True, default='')
    address_3 = models.CharField(max_length=40, blank=True, default='')
    city = models.CharField(max_length=35, blank=True, default='')
    state = models.CharField(max_length=30, blank=True, default='')
    pincode = models.CharField(max_length=6, blank=True, default='')

    # New Country Field
    country = models.CharField(max_length=35, blank=True, default='India')

    mobile = models.CharField(max_length=15, blank=True, default='')
    email = models.EmailField(blank=True)

    # New Fields for V183
    id_type = models.CharField(max_length=2, choices=ID_TYPE_CHOICES, blank=True)
    id_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"

class Document(models.Model):
    PAN_CARD = 'PAN'
    AADHAAR_CARD = 'AADHAAR'
    CANCELLED_CHEQUE = 'CHEQUE'
    OTHERS = 'OTHERS'

    DOCUMENT_TYPE_CHOICES = [
        (PAN_CARD, 'PAN Card'),
        (AADHAAR_CARD, 'Aadhaar Card'),
        (CANCELLED_CHEQUE, 'Cancelled Cheque'),
        (OTHERS, 'Others'),
    ]

    investor = models.ForeignKey(InvestorProfile, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=10, choices=DOCUMENT_TYPE_CHOICES, default=OTHERS)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.investor.user.username}"
