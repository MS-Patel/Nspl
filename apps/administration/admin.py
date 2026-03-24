from django.contrib import admin
from .models import SystemConfiguration

@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ('id', 'company_name', 'company_email')

    def has_add_permission(self, request):
        # Only allow adding if no instance exists
        if SystemConfiguration.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    fieldsets = (
        ('Company Details', {
            'fields': (
                'company_name', 'company_address', 'company_city',
                'company_state', 'company_pincode', 'company_country',
                'company_phone', 'company_email', 'company_website',
                'company_logo', 'gstin', 'arn_code'
            )
        }),
        ('Order Settings', {
            'fields': ('default_euin',)
        }),
        ('Report Settings', {
            'fields': ('report_disclaimer',)
        }),
        ('Maintenance Mode', {
            'fields': ('is_maintenance_mode',)
        }),
        ('RTA Mail Configuration', {
            'fields': (
                'rta_email_host', 'rta_email_port', 'rta_email_user',
                'rta_email_password', 'rta_file_passwords',
                'rta_email_sender_filters', 'rta_email_subject_filters',
                'rta_email_fetch_days'
            )
        }),
        ('Email Settings', {
            'fields': (
                'email_host', 'email_port', 'email_host_user',
                'email_host_password', 'email_use_tls', 'email_use_ssl',
                'default_from_email'
            )
        }),
    )
