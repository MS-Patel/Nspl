from django.contrib import admin
from .models import InvestorProfile, User
# Register your models here.

admin.site.register(User)  # Add your user model here inside the register() method
admin.site.register(InvestorProfile)  # Add your user model here inside the register() method