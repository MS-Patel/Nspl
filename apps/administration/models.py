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

    # Report Settings
    report_disclaimer = models.TextField(blank=True, null=True, default="Disclaimer: All values shown in this report are based on internal calculations and provided for informational purposes only. Please verify with official AMC statements.")

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

    # NDML KRA Configuration
    ndml_env = models.CharField(max_length=10, choices=[('DEMO', 'DEMO'), ('PROD', 'PROD')], default='DEMO', help_text="NDML Environment")
    ndml_user_name = models.CharField(max_length=100, blank=True, null=True, help_text="NDML API User Name")
    ndml_password = models.CharField(max_length=100, blank=True, null=True, help_text="NDML API Password")
    ndml_pos_code = models.CharField(max_length=50, blank=True, null=True, help_text="NDML POS Code")
    ndml_mi_id = models.CharField(max_length=50, blank=True, null=True, help_text="NDML MI ID")

    # RTA Mail Configuration
    rta_email_host = models.CharField(max_length=255, default="imap.gmail.com", help_text="IMAP Host for RTA emails")
    rta_email_port = models.IntegerField(default=993, help_text="IMAP Port for RTA emails")
    rta_email_user = models.CharField(max_length=255, blank=True, null=True, help_text="Email address for receiving RTA feeds")
    rta_email_password = models.CharField(max_length=255, blank=True, null=True, help_text="Password or App Password for RTA email")
    rta_file_passwords = models.CharField(max_length=500, blank=True, null=True, help_text="Comma-separated list of passwords for RTA ZIP files")
    rta_email_sender_filters = models.TextField(blank=True, null=True, help_text="Comma-separated list of sender emails (e.g., donotreply@camsonline.com)")
    rta_email_subject_filters = models.TextField(blank=True, null=True, help_text="Comma-separated list of email subjects to filter by")
    rta_email_fetch_days = models.IntegerField(default=3, help_text="Number of days to look back for RTA emails")

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
