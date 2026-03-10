from django.contrib import admin
from .models import (
    AMC, SchemeCategory, Scheme, NAVHistory,
    FundManager, SchemeManager, SchemeHolding,
    SchemeSectorAllocation, SchemeAssetAllocation
)

@admin.register(AMC)
class AMCAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code')
    search_fields = ('name', 'code')

@admin.register(SchemeCategory)
class SchemeCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code')
    search_fields = ('name', 'code')

@admin.register(FundManager)
class FundManagerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

class SchemeManagerInline(admin.TabularInline):
    model = SchemeManager
    extra = 1

class SchemeHoldingInline(admin.TabularInline):
    model = SchemeHolding
    extra = 1

class SchemeSectorAllocationInline(admin.TabularInline):
    model = SchemeSectorAllocation
    extra = 1

class SchemeAssetAllocationInline(admin.TabularInline):
    model = SchemeAssetAllocation
    extra = 1

@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'amc', 'scheme_code', 'isin', 'scheme_type', 'scheme_plan', 'channel_partner_code')
    search_fields = ('name', 'scheme_code', 'isin', 'rta_scheme_code','channel_partner_code')
    list_filter = ('amc', 'category', 'scheme_type', 'scheme_plan', 'riskometer', 'purchase_allowed', 'redemption_allowed', 'is_sip_allowed')
    inlines = [SchemeManagerInline, SchemeHoldingInline, SchemeSectorAllocationInline, SchemeAssetAllocationInline]

@admin.register(NAVHistory)
class NAVHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'scheme', 'nav_date', 'net_asset_value', 'repurchase_price', 'sale_price')
    search_fields = ('scheme__name', 'scheme__scheme_code')
    list_filter = ('nav_date',)
