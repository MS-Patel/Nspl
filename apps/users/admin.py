from django.contrib import admin
from .models import BankAccount, InvestorProfile, Nominee, User
# Register your models here.

admin.site.register(User)  # Add your user model here inside the register() method
admin.site.register(InvestorProfile)  # Add your user model here inside the register() method
admin.site.register(BankAccount)  # Add your user model here inside the register() method
admin.site.register(Nominee)  # Add your user model here inside the register() method