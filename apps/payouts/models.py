from django.db import models
from django.core.exceptions import ValidationError
from apps.products.models import SchemeCategory, AMC
from apps.users.models import User
from apps.reconciliation.models import Holding

class CommissionRule(models.Model):
    category = models.ForeignKey(SchemeCategory, on_delete=models.CASCADE, related_name='commission_rules')
    amc = models.ForeignKey(AMC, on_delete=models.CASCADE, null=True, blank=True, related_name='commission_rules', help_text="Leave blank to apply to all AMCs for this category")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('category', 'amc')
        verbose_name = "Commission Rule"
        verbose_name_plural = "Commission Rules"

    def __str__(self):
        if self.amc:
            return f"{self.category.name} - {self.amc.name}"
        return f"{self.category.name} - All AMCs"

class CommissionTier(models.Model):
    rule = models.ForeignKey(CommissionRule, on_delete=models.CASCADE, related_name='tiers')
    min_aum = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Minimum AUM (>=)")
    max_aum = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Maximum AUM (<). Leave blank for infinity.")
    rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Commission Rate in % (e.g. 0.80)")

    class Meta:
        ordering = ['min_aum']
        verbose_name = "Commission Tier"
        verbose_name_plural = "Commission Tiers"

    def __str__(self):
        max_str = f"{self.max_aum}" if self.max_aum else "Inf"
        return f"{self.min_aum} - {max_str} : {self.rate}%"

    def clean(self):
        if self.max_aum and self.min_aum >= self.max_aum:
            raise ValidationError("Max AUM must be greater than Min AUM")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

class Payout(models.Model):
    STATUS_DRAFT = 'DRAFT'
    STATUS_PAID = 'PAID'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PAID, 'Paid'),
    ]

    distributor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payouts', limit_choices_to={'user_type': 'DISTRIBUTOR'})
    period_date = models.DateField(help_text="The month/year this payout represents (usually 1st of month)")

    total_aum = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_commission = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    generated_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('distributor', 'period_date')
        ordering = ['-period_date', 'distributor']

    def __str__(self):
        return f"{self.distributor.name} - {self.period_date.strftime('%B %Y')}"

class PayoutDetail(models.Model):
    payout = models.ForeignKey(Payout, on_delete=models.CASCADE, related_name='details')
    holding = models.ForeignKey(Holding, on_delete=models.SET_NULL, null=True, blank=True, related_name='payout_details')

    # Denormalized fields for reporting preservation even if underlying objects change
    investor_name = models.CharField(max_length=255)
    scheme_name = models.CharField(max_length=255)
    folio_number = models.CharField(max_length=50, blank=True)
    category = models.CharField(max_length=100)
    amc_name = models.CharField(max_length=255)

    aum = models.DecimalField(max_digits=20, decimal_places=2, help_text="AUM used for calculation")
    applied_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Rate % applied")
    commission_amount = models.DecimalField(max_digits=15, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payout} - {self.scheme_name}"
