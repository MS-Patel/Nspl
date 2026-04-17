from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.indexes import BrinIndex
from simple_history.models import HistoricalRecords

class AMC(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, unique=True, help_text="AMC Code from BSE/RTA")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "AMC"
        verbose_name_plural = "AMCs"

    def __str__(self):
        return self.name

class SchemeCategory(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Scheme Category"
        verbose_name_plural = "Scheme Categories"

    def __str__(self):
        return self.name

class FundManager(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Scheme(models.Model):
    # Identifiers
    amc = models.ForeignKey(AMC, on_delete=models.CASCADE, related_name='schemes', null=True, blank=True)
    category = models.ForeignKey(SchemeCategory, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    isin = models.CharField(max_length=20, db_index=True)
    scheme_code = models.CharField(max_length=50, unique=True, null=True, blank=True, help_text="BSE Scheme Code (legacy)")
    unique_no = models.BigIntegerField(unique=True, null=True, blank=True, help_text="BSE Unique No")
    rta_scheme_code = models.CharField(max_length=50, blank=True, null=True)
    amc_scheme_code = models.CharField(max_length=50, blank=True, null=True)
    amfi_code = models.CharField(max_length=50, null=True, blank=True, help_text="AMFI Scheme Code")

    # Classification
    scheme_type = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. Open Ended")
    plan_type = models.CharField(
        max_length=50,
        choices=[("DIRECT", "Direct"), ("REGULAR", "Regular")],
        db_index=True, null=True, blank=True
    )
    option = models.CharField(
        max_length=50,
        choices=[("GROWTH", "Growth"), ("IDCW", "IDCW")],
        db_index=True, null=True, blank=True
    )
    scheme_plan = models.CharField(max_length=50, blank=True, null=True, help_text="Legacy e.g. NORMAL, DIRECT")

    # Purchase Rules
    purchase_allowed = models.BooleanField(default=True)
    purchase_transaction_mode = models.CharField(max_length=50, blank=True, null=True)
    min_purchase_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    additional_purchase_amount = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    max_purchase_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    purchase_amount_multiplier = models.DecimalField(max_digits=15, decimal_places=2, default=1)
    purchase_cutoff_time = models.TimeField(null=True, blank=True)

    # Redemption Rules
    redemption_allowed = models.BooleanField(default=True)
    redemption_transaction_mode = models.CharField(max_length=50, blank=True, null=True)
    min_redemption_qty = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    redemption_qty_multiplier = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    max_redemption_qty = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    min_redemption_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    max_redemption_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    redemption_amount_multiple = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    redemption_cutoff_time = models.TimeField(null=True, blank=True)

    # Features
    is_sip_allowed = models.BooleanField(default=False)
    is_stp_allowed = models.BooleanField(default=False)
    is_swp_allowed = models.BooleanField(default=False)
    is_switch_allowed = models.BooleanField(default=False)

    # Dates
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    reopening_date = models.DateField(null=True, blank=True)

    # Stats & Info
    aum = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text="Assets Under Management in Cr")
    expense_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Expense Ratio %")
    benchmark_index = models.CharField(max_length=255, null=True, blank=True)

    RISKOMETER_CHOICES = [
        ('Low', 'Low'),
        ('Low to Moderate', 'Low to Moderate'),
        ('Moderate', 'Moderate'),
        ('Moderately High', 'Moderately High'),
        ('High', 'High'),
        ('Very High', 'Very High'),
    ]
    riskometer = models.CharField(max_length=50, choices=RISKOMETER_CHOICES, null=True, blank=True)
    about_fund = models.TextField(null=True, blank=True)

    # Other
    face_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    settlement_type = models.CharField(max_length=20, blank=True, null=True)
    rta_agent_code = models.CharField(max_length=50, null=True, blank=True)
    amc_active_flag = models.BooleanField(default=True)
    dividend_reinvestment_flag = models.BooleanField(default=False)
    amc_ind = models.CharField(max_length=50, null=True, blank=True)
    exit_load_flag = models.BooleanField(default=False)
    exit_load = models.TextField(null=True, blank=True)
    lock_in_period_flag = models.BooleanField(default=False)
    lock_in_period = models.CharField(max_length=50, null=True, blank=True)
    channel_partner_code = models.CharField(max_length=50, null=True, blank=True)

    is_active = models.BooleanField(default=True, help_text="Set to False to disable this scheme for new investments.")

    # External APIs
    family_id = models.CharField(max_length=100, null=True, blank=True, help_text="mfdata.in Family ID", db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=["isin", "plan_type", "option"]),
            models.Index(fields=["amfi_code"]),
            models.Index(fields=["normalized_name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.isin})"


class BSESchemeMapping(models.Model):
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name="bse_mappings")
    bse_code = models.CharField(max_length=20, unique=True)
    transaction_type = models.CharField(
        max_length=10,
        choices=[("LUMPSUM", "LUMPSUM"), ("SIP", "SIP"), ("STP", "STP"), ("SWP", "SWP")]
    )
    min_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        indexes = [
            models.Index(fields=["scheme", "transaction_type"]),
            models.Index(fields=["bse_code"]),
        ]

    def __str__(self):
        return f"{self.bse_code} - {self.transaction_type} ({self.scheme.name})"


class RTASchemeMapping(models.Model):
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name="rta_mappings")
    rta_code = models.CharField(max_length=50, unique=True)
    rta_name = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        indexes = [
            models.Index(fields=["rta_code"]),
        ]

    def __str__(self):
        return f"{self.rta_code} ({self.scheme.name})"


class NAVHistory(models.Model):
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name='nav_history')
    nav_date = models.DateField(db_index=True)
    net_asset_value = models.DecimalField(max_digits=15, decimal_places=4)
    repurchase_price = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    sale_price = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)

    class Meta:
        unique_together = ('scheme', 'nav_date')
        ordering = ['-nav_date']
        get_latest_by = 'nav_date'
        indexes = [
            models.Index(fields=["scheme", "-nav_date"], name="navhist_scheme_date_idx"),
            BrinIndex(fields=["nav_date"], name="navhist_date_brin_idx"),
        ]

    def __str__(self):
        return f"{self.scheme.isin} - {self.nav_date} - {self.net_asset_value}"


class UnmatchedSchemeLog(models.Model):
    source = models.CharField(max_length=50, choices=[("AMFI", "AMFI"), ("BSE", "BSE"), ("RTA", "RTA")])
    raw_data = models.JSONField(help_text="The raw row data that failed to match")
    reason = models.TextField(help_text="Why it failed to match")
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Unmatched {self.source} log - {self.created_at}"


class SchemeManager(models.Model):
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name='managers')
    manager = models.ForeignKey(FundManager, on_delete=models.CASCADE, related_name='schemes')
    start_date = models.DateField(null=True, blank=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.manager.name} - {self.scheme.name}"

class SchemeHolding(models.Model):
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name='scheme_holdings')
    company_name = models.CharField(max_length=255)
    percentage = models.DecimalField(max_digits=8, decimal_places=2, help_text="Holding percentage (e.g. 5.50)")
    market_value = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text="Market Value")
    quantity = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True, help_text="Quantity")

    class Meta:
        ordering = ['-percentage']

    def __str__(self):
        return f"{self.company_name} ({self.percentage}%)"

class SchemeSectorAllocation(models.Model):
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name='sector_allocations')
    sector_name = models.CharField(max_length=100)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.sector_name} ({self.percentage}%)"

class SchemeAssetAllocation(models.Model):
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name='asset_allocations')
    asset_type = models.CharField(max_length=100, help_text="Equity, Debt, Cash, etc.")
    percentage = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.asset_type} ({self.percentage}%)"

class SchemeRatio(models.Model):
    scheme = models.OneToOneField(Scheme, on_delete=models.CASCADE, related_name='ratios')
    as_of_date = models.DateField(null=True, blank=True)

    # Valuation
    pe_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pb_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ps_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dividend_yield = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Efficiency
    roe = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    roa = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Returns
    sharpe_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    jensens_alpha = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    treynor_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    information_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Risk
    std_deviation = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    beta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sortino_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    r_squared = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Ratios for {self.scheme.name}"
