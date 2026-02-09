from django.db import models
from django.utils.translation import gettext_lazy as _

class AMC(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, unique=True, help_text="AMC Code from BSE/RTA")

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

class Scheme(models.Model):
    # Identifiers
    amc = models.ForeignKey(AMC, on_delete=models.CASCADE, related_name='schemes')
    category = models.ForeignKey(SchemeCategory, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    isin = models.CharField(max_length=20, db_index=True)
    scheme_code = models.CharField(max_length=50, unique=True, help_text="BSE Scheme Code")
    unique_no = models.BigIntegerField(unique=True, null=True, blank=True, help_text="BSE Unique No")
    rta_scheme_code = models.CharField(max_length=50, blank=True, null=True)
    amc_scheme_code = models.CharField(max_length=50, blank=True, null=True)

    # Classification
    scheme_type = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. Open Ended")
    scheme_plan = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. NORMAL, DIRECT")

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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.isin})"

class NAVHistory(models.Model):
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name='nav_history')
    nav_date = models.DateField()
    net_asset_value = models.DecimalField(max_digits=15, decimal_places=4)
    repurchase_price = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    sale_price = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)

    class Meta:
        unique_together = ('scheme', 'nav_date')
        ordering = ['-nav_date']
        get_latest_by = 'nav_date'

    def __str__(self):
        return f"{self.scheme.scheme_code} - {self.nav_date} - {self.net_asset_value}"
