from django.contrib import admin
from .models import AMC, SchemeCategory, Scheme, NAVHistory

@admin.register(AMC)
class AMCAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

@admin.register(SchemeCategory)
class SchemeCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    list_display = ('name', 'amc', 'scheme_code', 'isin', 'scheme_type', 'scheme_plan')
    search_fields = ('name', 'scheme_code', 'isin', 'rta_scheme_code')
    list_filter = ('amc', 'category', 'scheme_type', 'scheme_plan', 'purchase_allowed', 'redemption_allowed', 'is_sip_allowed')

@admin.register(NAVHistory)
class NAVHistoryAdmin(admin.ModelAdmin):
    list_display = ('scheme', 'nav_date', 'net_asset_value', 'repurchase_price', 'sale_price')
    search_fields = ('scheme__name', 'scheme__scheme_code')
    list_filter = ('nav_date',)
