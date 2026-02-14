from django.contrib import admin
from .models import SystemConfiguration

@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Only allow adding if no instance exists
        if SystemConfiguration.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False
