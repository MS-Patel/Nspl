from django.contrib import admin

from apps.investments.models import Mandate, Order

# Register your models here.


admin.site.register(Mandate)  # Add your investment models here
admin.site.register(Order)  # Add your investment models here