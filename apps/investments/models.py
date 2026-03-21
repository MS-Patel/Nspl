from django.db import models
from django.conf import settings
from apps.users.models import InvestorProfile, DistributorProfile, BankAccount
from apps.products.models import Scheme, AMC
from apps.administration.models import SystemConfiguration
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

    @property
    def is_bse_submitted(self):
        """
        Returns True if the mandate has been successfully submitted to BSE (i.e., has a real Mandate ID).
        Returns False if the submission failed (i.e., has a TEMP ID).
        """
        return not self.mandate_id.startswith('TEMP-')

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
    DAILY = 'DAILY'
    QUARTERLY = 'QUARTERLY'

    FREQUENCY_CHOICES = [
        (MONTHLY, 'Monthly'),
        (WEEKLY, 'Weekly'),
        (DAILY, 'Daily'),
        (QUARTERLY, 'Quarterly'),
    ]

    STATUS_ACTIVE = 'ACTIVE'
    STATUS_PAUSED = 'PAUSED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_PENDING = 'PENDING'
    STATUS_FAILED = 'FAILED'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_PAUSED, 'Paused'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_PENDING, 'Pending'),
        (STATUS_FAILED, 'Failed'),
    ]

    investor = models.ForeignKey(InvestorProfile, on_delete=models.CASCADE, related_name='sips')
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name='sips')
    folio = models.ForeignKey(Folio, on_delete=models.SET_NULL, null=True, blank=True, related_name='sips')
    mandate = models.ForeignKey(Mandate, on_delete=models.PROTECT, related_name='sips')

    amount = models.DecimalField(max_digits=15, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default=MONTHLY)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    installment_day = models.IntegerField(null=True, blank=True, help_text="Day of the month (e.g., 5 for 5th of every month)")
    installments = models.IntegerField(null=True, blank=True, help_text="Total number of installments")

    bse_sip_id = models.CharField(max_length=50, blank=True, null=True, help_text="BSE SIP Registration ID")
    bse_reg_no = models.CharField(max_length=50, blank=True, null=True, help_text="BSE XSIP Registration Number")

    # New Fields for Ref No and EUIN
    unique_ref_no = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    euin = models.CharField(max_length=50, blank=True, help_text="EUIN used for this transaction")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    last_alert_sent_date = models.DateField(null=True, blank=True, help_text="Last date an SMS alert was sent for an upcoming installment")
    next_installment_date = models.DateField(null=True, blank=True, help_text="Calculated date for the next SIP installment")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_next_installment_date(self, save=True):
        """Calculates the next installment date that is strictly in the future or today."""
        import datetime
        from dateutil.relativedelta import relativedelta
        if self.status != self.STATUS_ACTIVE:
            self.next_installment_date = None
            if save:
                self.save(update_fields=['next_installment_date'])
            return None

        today = datetime.date.today()
        # If the start_date is in the future, the next date is the start_date
        if self.start_date >= today:
            self.next_installment_date = self.start_date
            if save:
                self.save(update_fields=['next_installment_date'])
            return self.start_date

        # Calculate next date based on frequency
        current_date = self.start_date

        # Max loop limit to prevent infinite loops (e.g. daily for 100 years)
        max_installments = self.installments if self.installments > 0 else 1200
        count = 0

        while current_date < today and count < max_installments:
            if self.frequency == self.MONTHLY:
                current_date += relativedelta(months=1)
            elif self.frequency == self.WEEKLY:
                current_date += relativedelta(weeks=1)
            elif self.frequency == self.DAILY:
                current_date += relativedelta(days=1)
            elif self.frequency == self.QUARTERLY:
                current_date += relativedelta(months=3)
            else:
                break
            count += 1

        # If current_date is beyond end_date, it means SIP is completed/should be completed
        if self.end_date and current_date > self.end_date:
            self.next_installment_date = None
            if save:
                self.save(update_fields=['next_installment_date'])
            return None

        # Check if calculated date goes over number of installments
        if self.installments and self.installments > 0 and count >= self.installments:
            self.next_installment_date = None
            if save:
                self.save(update_fields=['next_installment_date'])
            return None

        self.next_installment_date = current_date
        if save:
            self.save(update_fields=['next_installment_date'])
        return current_date

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
                config = SystemConfiguration.get_solo()
                self.euin = config.default_euin or ""

        # Calculate next_installment_date automatically when saved and missing
        if not self.next_installment_date and self.status == self.STATUS_ACTIVE:
            self.calculate_next_installment_date(save=False)

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
    target_scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, null=True, blank=True, related_name='switch_orders', help_text="Target Scheme for Switch Orders")
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
    all_redeem = models.BooleanField(default=False, help_text="If True, redeem all units")

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
                config = SystemConfiguration.get_solo()
                self.euin = config.default_euin or ""

        super().save(*args, **kwargs)

class SIPInstallment(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_TRIGGERED = 'TRIGGERED'
    STATUS_SUCCESS = 'SUCCESS'
    STATUS_FAILED = 'FAILED'
    STATUS_SKIPPED = 'SKIPPED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_TRIGGERED, 'Triggered'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_SKIPPED, 'Skipped'),
    ]

    sip_master = models.ForeignKey(SIP, on_delete=models.CASCADE, related_name='sip_installments')
    due_date = models.DateField()
    expected_amount = models.DecimalField(max_digits=15, decimal_places=2)

    order_id = models.CharField(max_length=50, blank=True, null=True, help_text="BSE Order ID or Reg No")
    transaction = models.ForeignKey('reconciliation.Transaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='sip_installments')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    failure_reason = models.TextField(blank=True, null=True)
    retry_count = models.IntegerField(default=0)
    matched_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date']
        indexes = [
            models.Index(fields=['sip_master', 'due_date']),
            models.Index(fields=['status']),
            models.Index(fields=['order_id']),
            models.Index(fields=['transaction']),
        ]

    def __str__(self):
        return f"Installment {self.id} for SIP {self.sip_master_id} on {self.due_date}"
