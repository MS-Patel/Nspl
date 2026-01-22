from django.db import models
from django.conf import settings
from apps.users.models import InvestorProfile, DistributorProfile, BankAccount
from apps.products.models import Scheme, AMC
from apps.investments.constants import COMPANY_DEFAULT_EUIN
from apps.investments.utils import generate_distributor_based_ref
import uuid
import time
import random
import string

def generate_order_unique_ref_no():
    """
    Generates a unique reference number for orders, ensuring it is <= 20 characters
    to comply with BSE requirements.
    Format: {timestamp_ms}{random_6_chars}
    Example: 1705622400123ABCDEF (13 + 6 = 19 chars)
    DEPRECATED: Used in old migrations. New logic uses generate_distributor_based_ref in save().
    """
    # 13 digits for millis timestamp
    timestamp = int(time.time() * 1000)
    # 6 random digits
    suffix = ''.join(random.choices(string.digits, k=6))
    return f"{timestamp}{suffix}"

class Mandate(models.Model):
    # Status Choices
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]

    # Mandate Type Choices
    PHYSICAL = 'X'
    ISIP = 'I'
    NET_BANKING = 'N'

    MANDATE_TYPE_CHOICES = [
        (PHYSICAL, 'Physical (XSIP)'),
        (ISIP, 'E-Mandate (ISIP)'),
        (NET_BANKING, 'E-Mandate (Net Banking)'),
    ]

    investor = models.ForeignKey(InvestorProfile, on_delete=models.CASCADE, related_name='mandates')
    bank_account = models.ForeignKey(BankAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='mandates')
    mandate_id = models.CharField(max_length=50, unique=True, help_text="UMRN or Mandate ID from BSE")

    mandate_type = models.CharField(max_length=1, choices=MANDATE_TYPE_CHOICES, default='I', help_text="Type of Mandate")

    amount_limit = models.DecimalField(max_digits=15, decimal_places=2, help_text="Maximum amount allowed per transaction")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.mandate_id} - {self.investor.user.username}"

class Folio(models.Model):
    investor = models.ForeignKey(InvestorProfile, on_delete=models.CASCADE, related_name='folios')
    amc = models.ForeignKey(AMC, on_delete=models.CASCADE, related_name='folios')
    folio_number = models.CharField(max_length=50)

    # Optional: Cache values like current value, but for now keep it simple
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('investor', 'amc', 'folio_number')
        verbose_name = "Folio"
        verbose_name_plural = "Folios"

    def __str__(self):
        return f"{self.folio_number} - {self.amc.name}"

class SIP(models.Model):
    # Frequencies
    MONTHLY = 'MONTHLY'
    WEEKLY = 'WEEKLY'
    QUARTERLY = 'QUARTERLY'

    FREQUENCY_CHOICES = [
        (MONTHLY, 'Monthly'),
        (WEEKLY, 'Weekly'),
        (QUARTERLY, 'Quarterly'),
    ]

    STATUS_ACTIVE = 'ACTIVE'
    STATUS_PAUSED = 'PAUSED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_PENDING = 'PENDING'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_PAUSED, 'Paused'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_PENDING, 'Pending'),
    ]

    investor = models.ForeignKey(InvestorProfile, on_delete=models.CASCADE, related_name='sips')
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name='sips')
    folio = models.ForeignKey(Folio, on_delete=models.SET_NULL, null=True, blank=True, related_name='sips')
    mandate = models.ForeignKey(Mandate, on_delete=models.PROTECT, related_name='sips')

    amount = models.DecimalField(max_digits=15, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default=MONTHLY)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    installments = models.IntegerField(help_text="Number of installments")

    bse_sip_id = models.CharField(max_length=50, blank=True, null=True, help_text="BSE SIP Registration ID")
    bse_reg_no = models.CharField(max_length=50, blank=True, null=True, help_text="BSE XSIP Registration Number")

    # New Fields for Ref No and EUIN
    unique_ref_no = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    euin = models.CharField(max_length=50, blank=True, help_text="EUIN used for this transaction")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SIP - {self.investor.user.username} - {self.scheme.name} - {self.amount}"

    def save(self, *args, **kwargs):
        """
        Overrides save to generate unique_ref_no and populate EUIN.
        NOTE: These automated fields will NOT be populated if using bulk_create.
        """
        # Generate Unique Ref No if not present
        if not self.unique_ref_no:
            # SIP uses investor's distributor as it doesn't have a direct distributor field usually
            dist_id = 0
            if self.investor and self.investor.distributor:
                dist_id = self.investor.distributor.id
            self.unique_ref_no = generate_distributor_based_ref(dist_id)

        # Auto-fill EUIN
        if not self.euin:
            if self.investor.distributor and self.investor.distributor.euin:
                self.euin = self.investor.distributor.euin
            else:
                self.euin = COMPANY_DEFAULT_EUIN

        super().save(*args, **kwargs)

class Order(models.Model):
    # Transaction Types
    PURCHASE = 'P'
    REDEMPTION = 'R'
    SWITCH = 'S'
    SIP = 'SIP' # SIP Registration

    TXN_TYPE_CHOICES = [
        (PURCHASE, 'Lumpsum Purchase'),
        (REDEMPTION, 'Redemption'),
        (SWITCH, 'Switch'),
        (SIP, 'SIP Registration'),
    ]

    # Status
    PENDING = 'PENDING'
    SENT_TO_BSE = 'SENT_TO_BSE'
    AWAITING_PAYMENT = 'AWAITING_PAYMENT'
    APPROVED = 'APPROVED' # By BSE/RTA
    REJECTED = 'REJECTED'
    ALLOTTED = 'ALLOTTED'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (SENT_TO_BSE, 'Sent to BSE'),
        (AWAITING_PAYMENT, 'Awaiting Payment'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (ALLOTTED, 'Allotted'),
    ]

    # Payment Modes
    DIRECT = 'DIRECT' # Netbanking
    UPI = 'UPI'
    NEFT = 'NEFT'
    MANDATE = 'MANDATE' # For SIP or One-time Mandate

    PAYMENT_MODE_CHOICES = [
        (DIRECT, 'Net Banking'),
        (UPI, 'UPI'),
        (NEFT, 'NEFT/RTGS'),
        (MANDATE, 'Mandate'),
    ]

    # Core Relationships
    investor = models.ForeignKey(InvestorProfile, on_delete=models.CASCADE, related_name='orders')
    distributor = models.ForeignKey(DistributorProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name='orders')
    folio = models.ForeignKey(Folio, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', help_text="Linked Folio if existing")
    mandate = models.ForeignKey(Mandate, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', help_text="Required for SIP")
    sip_reg = models.ForeignKey(SIP, on_delete=models.SET_NULL, null=True, blank=True, related_name='registration_orders', help_text="Linked SIP Registration")

    # Transaction Details
    transaction_type = models.CharField(max_length=10, choices=TXN_TYPE_CHOICES, default=PURCHASE)
    amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Investment Amount")
    units = models.DecimalField(max_digits=15, decimal_places=4, default=0, help_text="Units for Redemption/Switch")
    allotted_units = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)

    # BSE Specifics
    # Removed default=generate_order_unique_ref_no to use save() logic
    unique_ref_no = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    bse_order_id = models.CharField(max_length=20, blank=True, null=True)
    bse_remarks = models.TextField(blank=True, null=True)

    euin = models.CharField(max_length=50, blank=True, help_text="EUIN used for this transaction")

    # Payment Details
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES, default=DIRECT)
    payment_ref_no = models.CharField(max_length=100, blank=True, null=True)
    payment_link = models.URLField(blank=True, null=True)

    # Flags
    is_new_folio = models.BooleanField(default=False, help_text="If True, request new folio creation")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.unique_ref_no} - {self.investor.user.username} - {self.scheme.name}"

    def save(self, *args, **kwargs):
        """
        Overrides save to generate unique_ref_no and populate EUIN.
        NOTE: These automated fields will NOT be populated if using bulk_create.
        """
        # Generate Unique Ref No if not present
        if not self.unique_ref_no:
            dist_id = self.distributor.id if self.distributor else 0
            self.unique_ref_no = generate_distributor_based_ref(dist_id)

        # Auto-fill EUIN
        if not self.euin:
            if self.distributor and self.distributor.euin:
                self.euin = self.distributor.euin
            else:
                self.euin = COMPANY_DEFAULT_EUIN

        super().save(*args, **kwargs)
