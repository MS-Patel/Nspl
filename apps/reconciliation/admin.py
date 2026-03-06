from django.contrib import admin
from .models import RTAFile, Transaction, Holding

@admin.register(RTAFile)
class RTAFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'rta_type', 'file_name', 'status', 'uploaded_at', 'processed_at')
    search_fields = ('file_name', 'rta_type')
    list_filter = ('rta_type', 'status', 'uploaded_at')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'investor', 'folio_number', 'original_txn_number', 'txn_type_code', 'txn_type', 'txn_action', 'description','nav','units','amount', 'date')
    search_fields = ('investor__user__username', 'folio_number', 'original_txn_number', 'scheme__name')
    list_filter = ('rta_code', 'date', 'txn_type_code')

@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):
    list_display = ('id', 'investor', 'scheme', 'folio_number', 'units', 'current_value', 'last_updated')
    search_fields = ('investor__user__username', 'folio_number', 'scheme__name', 'investor__pan')
    list_filter = ('scheme__amc', 'last_updated')
