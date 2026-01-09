from django.db import models
from django.conf import settings
from apps.users.models import InvestorProfile, DistributorProfile
from apps.products.models import Scheme, AMC
import uuid

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

class Order(models.Model):
    # Transaction Types
    PURCHASE = 'P'
    REDEMPTION = 'R'
    SWITCH = 'S'
    SIP_REGISTRATION = 'SIP'

    TXN_TYPE_CHOICES = [
        (PURCHASE, 'Purchase'),
        (REDEMPTION, 'Redemption'),
        (SWITCH, 'Switch'),
        (SIP_REGISTRATION, 'SIP Registration'),
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

    # Transaction Details
    transaction_type = models.CharField(max_length=10, choices=TXN_TYPE_CHOICES, default=PURCHASE)
    amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Investment Amount")
    units = models.DecimalField(max_digits=15, decimal_places=4, default=0, help_text="Units for Redemption/Switch")
    allotted_units = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)

    # BSE Specifics
    unique_ref_no = models.CharField(max_length=50, unique=True, default=uuid.uuid4, editable=False)
    bse_order_id = models.CharField(max_length=50, blank=True, null=True)
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
        # Auto-fill EUIN from Distributor if not set
        if not self.euin and self.distributor:
            self.euin = self.distributor.euin
        # Fallback to Company EUIN if still empty? (Can be handled in View or here if we import settings)
        # For now, leaving it blank if distributor has none, to be handled by business logic
        super().save(*args, **kwargs)
