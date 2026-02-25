from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from apps.users.models import DistributorProfile

class DistributorCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    min_aum = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Minimum AUM in Rupees")
    max_aum = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Maximum AUM in Rupees (Leave blank for infinity)")
    share_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage of brokerage given to distributor (e.g., 60.00)")

    class Meta:
        verbose_name_plural = "Distributor Categories"
        ordering = ['min_aum']

    def __str__(self):
        return f"{self.name} ({self.share_percentage}%)"

    def clean(self):
        if self.max_aum and self.min_aum >= self.max_aum:
            raise ValidationError("Max AUM must be greater than Min AUM")

class BrokerageImport(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_PROCESSING = 'PROCESSING'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_FAILED = 'FAILED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]

    month = models.IntegerField(choices=[(i, i) for i in range(1, 13)])
    year = models.IntegerField()
    cams_file = models.FileField(upload_to='brokerage/cams/%Y/%m/', null=True, blank=True)
    karvy_file = models.FileField(upload_to='brokerage/karvy/%Y/%m/', null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_log = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-year', '-month']
        unique_together = ('month', 'year')

    def __str__(self):
        return f"Brokerage Import - {self.get_month_display() if hasattr(self, 'get_month_display') else self.month}/{self.year}"

class BrokerageTransaction(models.Model):
    SOURCE_CAMS = 'CAMS'
    SOURCE_KARVY = 'KARVY'
    SOURCE_CHOICES = [
        (SOURCE_CAMS, 'CAMS'),
        (SOURCE_KARVY, 'Karvy'),
    ]

    import_file = models.ForeignKey(BrokerageImport, on_delete=models.CASCADE, related_name='transactions')
    distributor = models.ForeignKey(DistributorProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='brokerage_transactions')
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)

    # Raw Details
    transaction_date = models.DateField(null=True, blank=True)
    investor_name = models.CharField(max_length=255, blank=True)
    folio_number = models.CharField(max_length=50, blank=True)
    scheme_name = models.CharField(max_length=255, blank=True)
    scheme = models.ForeignKey('products.Scheme', on_delete=models.SET_NULL, null=True, blank=True, related_name='brokerage_transactions')
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Commission
    brokerage_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Audit
    is_mapped = models.BooleanField(default=False)
    mapping_remark = models.CharField(max_length=255, blank=True) # e.g. "Mapped via ARN", "Mapped via PAN"

    raw_data = models.JSONField(default=dict, blank=True) # To store full original row

    def __str__(self):
        return f"{self.source} - {self.investor_name} - {self.brokerage_amount}"

class Payout(models.Model):
    STATUS_CALCULATED = 'CALCULATED'
    STATUS_PAID = 'PAID'
    STATUS_CHOICES = [
        (STATUS_CALCULATED, 'Calculated'),
        (STATUS_PAID, 'Paid'),
    ]

    brokerage_import = models.ForeignKey(BrokerageImport, on_delete=models.CASCADE, related_name='payouts')
    distributor = models.ForeignKey(DistributorProfile, on_delete=models.CASCADE, related_name='payouts')

    # Snapshot of Distributor Status at time of calculation
    total_aum = models.DecimalField(max_digits=20, decimal_places=2, default=0, help_text="Total AUM of Distributor at time of calculation")
    category = models.CharField(max_length=100, blank=True) # e.g. "Gold"
    share_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Amounts
    gross_brokerage = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Total brokerage received from RTA")
    payable_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Amount payable to Distributor")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CALCULATED)
    generated_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-brokerage_import__year', '-brokerage_import__month', 'distributor']

    def __str__(self):
        return f"{self.distributor.user.username} - {self.payable_amount}"

class FolioDistributorMapping(models.Model):
    folio_number = models.CharField(max_length=50, unique=True, db_index=True)
    distributor = models.ForeignKey(DistributorProfile, on_delete=models.CASCADE, related_name='folio_mappings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.folio_number} -> {self.distributor.user.username}"
