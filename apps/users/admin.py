from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import BankAccount, InvestorProfile, Nominee, User, Branch, RMProfile, DistributorProfile, Document

# Register your models here.

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'name', 'user_type', 'is_staff')
    search_fields = ('username', 'email', 'name')
    list_filter = ('user_type', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('user_type', 'name')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('user_type', 'name', 'email')}),
    )

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

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('investor', 'bank_name', 'account_number', 'ifsc_code', 'account_type', 'is_default')
    search_fields = ('investor__user__username', 'account_number', 'bank_name', 'ifsc_code')
    list_filter = ('account_type', 'is_default')

@admin.register(Nominee)
class NomineeAdmin(admin.ModelAdmin):
    list_display = ('name', 'investor', 'relationship', 'percentage', 'id_type')
    search_fields = ('name', 'investor__user__username', 'pan', 'guardian_name')
    list_filter = ('relationship', 'id_type')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('investor', 'document_type', 'uploaded_at', 'description')
    search_fields = ('investor__user__username', 'investor__pan', 'description')
    list_filter = ('document_type', 'uploaded_at')
