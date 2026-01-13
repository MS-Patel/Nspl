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

class RMProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='rm_profile')
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

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='investor_profile')
    distributor = models.ForeignKey(DistributorProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='investors')

    # Basic Info
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

    # BSE Specific Fields
    tax_status = models.CharField(max_length=2, choices=TAX_STATUS_CHOICES, default=INDIVIDUAL)
    occupation = models.CharField(max_length=2, choices=OCCUPATION_CHOICES, default=SERVICE)
    holding_nature = models.CharField(max_length=2, choices=HOLDING_CHOICES, default=SINGLE)

    # Optional/Conditional Fields
    second_applicant_name = models.CharField(max_length=70, blank=True)
    second_applicant_pan = models.CharField(max_length=10, blank=True)
    third_applicant_name = models.CharField(max_length=70, blank=True)
    third_applicant_pan = models.CharField(max_length=10, blank=True)

    guardian_name = models.CharField(max_length=70, blank=True, help_text="Required if Tax Status is Minor")
    guardian_pan = models.CharField(max_length=10, blank=True, help_text="Required if Tax Status is Minor")

    # Status Flags
    kyc_status = models.BooleanField(default=False)
    ucc_code = models.CharField(max_length=20, blank=True, null=True, help_text="Unique Client Code from BSE")

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
    investor = models.ForeignKey(InvestorProfile, on_delete=models.CASCADE, related_name='nominees')
    name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage of allocation")
    date_of_birth = models.DateField(null=True, blank=True, help_text="Required if nominee is a minor")
    guardian_name = models.CharField(max_length=100, blank=True, help_text="If nominee is a minor")
    guardian_pan = models.CharField(max_length=10, blank=True, help_text="If nominee is a minor")

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
