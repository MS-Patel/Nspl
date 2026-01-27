from django.contrib import admin
from .models import DistributorCategory, BrokerageImport, BrokerageTransaction, Payout

@admin.register(DistributorCategory)
class DistributorCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_aum', 'max_aum', 'share_percentage')
    search_fields = ('name',)

@admin.register(BrokerageImport)
class BrokerageImportAdmin(admin.ModelAdmin):
    list_display = ('month', 'year', 'status', 'uploaded_at')
    list_filter = ('status', 'year')
    search_fields = ('year', 'month')

@admin.register(BrokerageTransaction)
class BrokerageTransactionAdmin(admin.ModelAdmin):
    list_display = ('source', 'transaction_date', 'investor_name', 'scheme_name', 'amount', 'brokerage_amount', 'distributor', 'is_mapped')
    list_filter = ('source', 'is_mapped', 'import_file')
    search_fields = ('investor_name', 'folio_number', 'distributor__user__username', 'scheme_name')

@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ('distributor', 'total_aum', 'category', 'gross_brokerage', 'share_percentage', 'payable_amount', 'status')
    list_filter = ('status', 'category', 'brokerage_import')
    search_fields = ('distributor__user__username', 'distributor__arn_number', 'category')
