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
    txn_type_code = models.CharField(max_length=100, help_text="Raw transaction type from RTA")
    txn_number = models.CharField(max_length=100, unique=True, help_text="Unique Reference No from RTA")
    original_txn_number = models.CharField(max_length=100, null=True, blank=True, help_text="Original RTA Transaction No for display")

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
    load_amount = models.DecimalField(max_digits=15, decimal_places=4, default=0, help_text="Exit Load Amount")
    tax_amount = models.DecimalField(max_digits=15, decimal_places=4, default=0, help_text="TDS/Tax Amount")

    # Distributor / Broker Details
    broker_code = models.CharField(max_length=50, blank=True, null=True, help_text="ARN Code")
    sub_broker_code = models.CharField(max_length=50, blank=True, null=True)
    euin = models.CharField(max_length=50, blank=True, null=True)
    
    # New Fields for Reporting
    amc_code = models.CharField(max_length=20, blank=True, null=True)
    product_code = models.CharField(max_length=20, blank=True, null=True)
    txn_nature = models.CharField(max_length=100, blank=True, null=True, help_text="Transaction Nature from RTA")
    tax_status = models.CharField(max_length=50, blank=True, null=True)
    micr_no = models.CharField(max_length=50, blank=True, null=True)
    old_folio = models.CharField(max_length=50, blank=True, null=True)
    reinvest_flag = models.CharField(max_length=10, blank=True, null=True)
    mult_brok = models.CharField(max_length=10, blank=True, null=True)
    scan_ref_no = models.CharField(max_length=100, blank=True, null=True)
    pan = models.CharField(max_length=20, blank=True, null=True)
    min_no = models.CharField(max_length=50, blank=True, null=True)
    targ_src_scheme = models.CharField(max_length=100, blank=True, null=True)
    ticob_trtype = models.CharField(max_length=50, blank=True, null=True)
    ticob_trno = models.CharField(max_length=50, blank=True, null=True)
    ticob_posted_date = models.DateField(null=True, blank=True)
    dp_id = models.CharField(max_length=50, blank=True, null=True)
    trxn_charges = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    eligib_amt = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    src_of_txn = models.CharField(max_length=50, blank=True, null=True)
    trxn_suffix = models.CharField(max_length=50, blank=True, null=True)
    siptrxnno = models.CharField(max_length=50, blank=True, null=True)
    ter_location = models.CharField(max_length=50, blank=True, null=True)
    euin_valid = models.CharField(max_length=10, blank=True, null=True)
    euin_opted = models.CharField(max_length=10, blank=True, null=True)
    sub_brk_arn = models.CharField(max_length=50, blank=True, null=True)
    exch_dc_flag = models.CharField(max_length=10, blank=True, null=True)
    src_brk_code = models.CharField(max_length=50, blank=True, null=True)
    sys_regn_date = models.DateField(null=True, blank=True)
    ac_no = models.CharField(max_length=50, blank=True, null=True)
    reversal_code = models.CharField(max_length=50, blank=True, null=True)
    exchange_flag = models.CharField(max_length=10, blank=True, null=True)
    ca_initiated_date = models.DateField(null=True, blank=True)
    gst_state_code = models.CharField(max_length=10, blank=True, null=True)
    igst_amount = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    cgst_amount = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    sgst_amount = models.DecimalField(max_digits=15, decimal_places=4, default=0)


    # Bank / Payment Details
    bank_account_no = models.CharField(max_length=50, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    payment_mode = models.CharField(max_length=50, blank=True, null=True)
    instrument_no = models.CharField(max_length=50, blank=True, null=True)
    instrument_date = models.DateField(null=True, blank=True)

    # Status / Location
    status_desc = models.CharField(max_length=100, blank=True, null=True, help_text="Raw Status from RTA")
    remarks = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)

    description = models.CharField(max_length=255, blank=True)
    tr_flag = models.CharField(max_length=100, blank=True, null=True, help_text="Transaction Flag from RTA (e.g., P, R)")

    # Future Proofing
    raw_data = models.JSONField(default=dict, blank=True, help_text="Full raw row data from source file")

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
