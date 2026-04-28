from simple_history.admin import SimpleHistoryAdmin
from import_export.admin import ImportExportModelAdmin, ImportExportMixin
from .models import BSESchemeMapping, RTASchemeMapping, UnmatchedSchemeLog

from django.contrib import admin
from .models import (
    AMC, SchemeCategory, Scheme, NAVHistory,
    FundManager, SchemeManager, SchemeHolding,
    SchemeSectorAllocation, SchemeAssetAllocation,
    SchemeRatio
)

@admin.register(AMC)
class AMCAdmin(ImportExportModelAdmin):
    list_display = ('id', 'name', 'code')
    search_fields = ('name', 'code')

@admin.register(SchemeCategory)
class SchemeCategoryAdmin(ImportExportModelAdmin):
    list_display = ('id', 'name', 'code')
    search_fields = ('name', 'code')

@admin.register(FundManager)
class FundManagerAdmin(ImportExportModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(SchemeManager)
class SchemeManagerAdmin(ImportExportModelAdmin):
    list_display = ('id', 'scheme', 'manager', 'start_date', 'is_primary')
    search_fields = ('scheme__name', 'manager__name')
    list_filter = ('is_primary',)

@admin.register(SchemeHolding)
class SchemeHoldingAdmin(ImportExportModelAdmin):
    list_display = ('id', 'scheme', 'company_name', 'percentage', 'market_value', 'quantity')
    search_fields = ('scheme__name', 'company_name')

@admin.register(SchemeSectorAllocation)
class SchemeSectorAllocationAdmin(ImportExportModelAdmin):
    list_display = ('id', 'scheme', 'sector_name', 'percentage')
    search_fields = ('scheme__name', 'sector_name')

@admin.register(SchemeAssetAllocation)
class SchemeAssetAllocationAdmin(ImportExportModelAdmin):
    list_display = ('id', 'scheme', 'asset_type', 'percentage')
    search_fields = ('scheme__name', 'asset_type')

@admin.register(SchemeRatio)
class SchemeRatioAdmin(ImportExportModelAdmin):
    list_display = ('id', 'scheme', 'as_of_date', 'pe_ratio', 'pb_ratio')
    search_fields = ('scheme__name',)

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
class SchemeAdmin(ImportExportMixin, SimpleHistoryAdmin):
    list_display = ('id', 'name', 'amc', 'scheme_code', 'isin', 'scheme_type', 'scheme_plan', 'channel_partner_code')
    search_fields = ('name', 'scheme_code', 'isin', 'rta_scheme_code','channel_partner_code')
    list_filter = ('amc', 'category', 'scheme_type', 'scheme_plan', 'riskometer', 'purchase_allowed', 'redemption_allowed', 'is_sip_allowed')
    inlines = [SchemeManagerInline, SchemeHoldingInline, SchemeSectorAllocationInline, SchemeAssetAllocationInline]

@admin.register(NAVHistory)
class NAVHistoryAdmin(ImportExportModelAdmin):
    list_display = ('id', 'scheme', 'nav_date', 'net_asset_value', 'repurchase_price', 'sale_price')
    search_fields = ('scheme__name', 'scheme__scheme_code')
    list_filter = ('nav_date',)

@admin.register(BSESchemeMapping)
class BSESchemeMappingAdmin(ImportExportMixin, SimpleHistoryAdmin):
    list_display = ('bse_code', 'scheme', 'transaction_type', 'is_active')
    search_fields = ('bse_code', 'scheme__name', 'scheme__isin')
    list_filter = ('transaction_type', 'is_active')

@admin.register(RTASchemeMapping)
class RTASchemeMappingAdmin(ImportExportMixin, SimpleHistoryAdmin):
    list_display = ('rta_code', 'rta_name', 'scheme')
    search_fields = ('rta_code', 'rta_name', 'scheme__name', 'scheme__isin')

@admin.register(UnmatchedSchemeLog)
class UnmatchedSchemeLogAdmin(ImportExportModelAdmin):
    list_display = ('source', 'reason', 'resolved', 'created_at')
    list_filter = ('source', 'resolved', 'created_at')
    search_fields = ('reason', 'raw_data')
