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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='investor_profile')
    distributor = models.ForeignKey(DistributorProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='investors')

    pan = models.CharField(max_length=10, unique=True)
    dob = models.DateField(null=True, blank=True, verbose_name="Date of Birth")
    gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], blank=True)
    mobile = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)

    # Placeholder for future KYC/BSE fields
    kyc_status = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} (PAN-{self.pan})"
