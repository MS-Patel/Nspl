from django.contrib import admin
from .models import BankAccount, InvestorProfile, Nominee, User, Branch, RMProfile, DistributorProfile

# Register your models here.

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'city', 'state')
    search_fields = ('name', 'code', 'city')

@admin.register(RMProfile)
class RMProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_code', 'branch')
    search_fields = ('user__username', 'user__name', 'employee_code')
    list_filter = ('branch',)

@admin.register(DistributorProfile)
class DistributorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'arn_number', 'rm', 'parent')
    search_fields = ('user__username', 'user__name', 'arn_number')
    list_filter = ('rm__branch',)

@admin.register(InvestorProfile)
class InvestorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'pan', 'distributor', 'rm', 'branch', 'kyc_status')
    search_fields = ('user__username', 'user__name', 'pan')
    list_filter = ('distributor', 'rm', 'branch', 'kyc_status')
    autocomplete_fields = ['distributor', 'rm', 'branch']

admin.site.register(User)
admin.site.register(BankAccount)
admin.site.register(Nominee)
