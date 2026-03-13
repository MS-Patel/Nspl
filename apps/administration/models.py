from django.db import models
from django.core.cache import cache

class SystemConfiguration(models.Model):
    # Company Details
    company_name = models.CharField(max_length=255, default="My Company")
    company_address = models.TextField(blank=True, null=True)
    company_city = models.CharField(max_length=100, blank=True, null=True)
    company_state = models.CharField(max_length=100, blank=True, null=True)
    company_pincode = models.CharField(max_length=20, blank=True, null=True)
    company_country = models.CharField(max_length=100, blank=True, null=True, default="India")
    company_phone = models.CharField(max_length=20, blank=True, null=True)
    company_email = models.EmailField(blank=True, null=True)
    company_website = models.URLField(blank=True, null=True)
    company_logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    gstin = models.CharField(max_length=20, blank=True, null=True)
    arn_code = models.CharField(max_length=50, blank=True, null=True, help_text="ARN Code for placing orders")

    # Order Settings
    default_euin = models.CharField(max_length=50, blank=True, null=True, help_text="Default EUIN used if order has none")

    # Maintenance Mode
    is_maintenance_mode = models.BooleanField(default=False, help_text="Enable to put the system in maintenance mode and lock out non-admin users.")

    # Email Settings
    email_host = models.CharField(max_length=255, default="smtp.gmail.com")
    email_port = models.IntegerField(default=587)
    email_host_user = models.CharField(max_length=255, blank=True, null=True)
    email_host_password = models.CharField(max_length=255, blank=True, null=True)
    email_use_tls = models.BooleanField(default=True)
    email_use_ssl = models.BooleanField(default=False)
    default_from_email = models.EmailField(default="noreply@example.com")

    class Meta:
        verbose_name = "System Configuration"
        verbose_name_plural = "System Configuration"

    def save(self, *args, **kwargs):
        self.pk = 1
        super(SystemConfiguration, self).save(*args, **kwargs)
        cache.set('system_configuration', self)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_solo(cls):
        obj = cache.get('system_configuration')
        if obj is None:
            obj, created = cls.objects.get_or_create(pk=1)
            cache.set('system_configuration', obj)
        return obj

    def __str__(self):
        return "System Configuration"
