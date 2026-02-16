from django.db import models
from apps.users.models import InvestorProfile
from apps.products.models import Scheme, AMC

class RTAFile(models.Model):
    """
    Tracks uploaded RTA Mailback files (CAMS/Karvy/Franklin).
    """
    RTA_CAMS = 'CAMS'
    RTA_KARVY = 'KARVY'
    RTA_FRANKLIN = 'FRANKLIN'

    RTA_CHOICES = [
        (RTA_CAMS, 'CAMS'),
        (RTA_KARVY, 'Karvy (KFintech)'),
        (RTA_FRANKLIN, 'Franklin Templeton'),
    ]

    STATUS_PENDING = 'PENDING'
    STATUS_PROCESSED = 'PROCESSED'
    STATUS_FAILED = 'FAILED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSED, 'Processed'),
        (STATUS_FAILED, 'Failed'),
    ]

    rta_type = models.CharField(max_length=20, choices=RTA_CHOICES)
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to='rta_files/%Y/%m/%d/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_log = models.TextField(blank=True, null=True)
    error_file = models.FileField(upload_to='rta_errors/%Y/%m/%d/', blank=True, null=True)

    def __str__(self):
        return f"{self.rta_type} - {self.file_name}"

class Transaction(models.Model):
    """
    Historical Transaction Record (WBR9).
    Source of truth for what happened.
    """
    TXN_PURCHASE = 'P'
    TXN_REDEMPTION = 'R'
    TXN_SWITCH_IN = 'SI'
    TXN_SWITCH_OUT = 'SO'
    TXN_SIP = 'SIP'
    # Add more as needed based on RTA codes

    SOURCE_RTA = 'RTA'
    SOURCE_BSE = 'BSE'
    SOURCE_MANUAL = 'MANUAL'

    SOURCE_CHOICES = [
        (SOURCE_RTA, 'RTA Mailback'),
        (SOURCE_BSE, 'BSE Star MF'),
        (SOURCE_MANUAL, 'Manual Entry'),
    ]

    investor = models.ForeignKey(InvestorProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='rta_transactions')
    scheme = models.ForeignKey(Scheme, on_delete=models.SET_NULL, null=True, blank=True, related_name='rta_transactions')
    folio_number = models.CharField(max_length=50)

    # RTA Fields
    rta_code = models.CharField(max_length=20, help_text="CAMS/Karvy")
    txn_type_code = models.CharField(max_length=20, help_text="Raw transaction type from RTA")
    txn_number = models.CharField(max_length=100, unique=True, help_text="Unique Reference No from RTA")

    # Matching / Provisional Fields
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_RTA)
    is_provisional = models.BooleanField(default=False, help_text="True if sourced from BSE allotment but not yet confirmed by RTA")
    bse_order_id = models.CharField(max_length=50, null=True, blank=True, help_text="BSE Order ID for matching")

    date = models.DateField()
    amount = models.DecimalField(max_digits=20, decimal_places=4)
    units = models.DecimalField(max_digits=20, decimal_places=4)
    nav = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)

    # Tax/Load
    stt = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    stamp_duty = models.DecimalField(max_digits=15, decimal_places=4, default=0)

    description = models.CharField(max_length=255, blank=True)
    tr_flag = models.CharField(max_length=20, blank=True, null=True, help_text="Transaction Flag from RTA (e.g., P, R)")

    # Metadata
    source_file = models.ForeignKey(RTAFile, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['folio_number', 'scheme']),
            models.Index(fields=['txn_number']),
            models.Index(fields=['bse_order_id']),
        ]

    def __str__(self):
        return f"{self.folio_number} - {self.scheme} - {self.amount} ({self.source})"

class Holding(models.Model):
    """
    Current Snapshot of Holdings.
    Aggregated from Transactions.
    """
    investor = models.ForeignKey(InvestorProfile, on_delete=models.CASCADE, related_name='holdings')
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name='holdings')
    folio_number = models.CharField(max_length=50)

    units = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    # Detailed Unit Breakdown
    free_units = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    locked_units = models.DecimalField(max_digits=20, decimal_places=4, default=0, help_text="ELSS Locked Units")
    pledged_units = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    average_cost = models.DecimalField(max_digits=20, decimal_places=4, default=0, help_text="Weighted Average Cost")

    # Valuation (Updated daily via NAV sync)
    current_nav = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    current_value = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('investor', 'scheme', 'folio_number')
        ordering = ['investor', 'scheme']

    def __str__(self):
        return f"{self.folio_number} - {self.scheme} - Units: {self.units}"
