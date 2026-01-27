from django.contrib import admin
from apps.investments.models import Mandate, Folio, SIP, Order

@admin.register(Mandate)
class MandateAdmin(admin.ModelAdmin):
    list_display = ('investor', 'mandate_id', 'amount_limit', 'status', 'mandate_type', 'start_date', 'end_date')
    search_fields = ('investor__user__username', 'investor__pan', 'mandate_id')
    list_filter = ('status', 'mandate_type', 'start_date')

@admin.register(Folio)
class FolioAdmin(admin.ModelAdmin):
    list_display = ('investor', 'amc', 'folio_number')
    search_fields = ('investor__user__username', 'folio_number', 'amc__name')
    list_filter = ('amc',)

@admin.register(SIP)
class SIPAdmin(admin.ModelAdmin):
    list_display = ('investor', 'scheme', 'amount', 'frequency', 'status', 'start_date', 'installments')
    search_fields = ('investor__user__username', 'scheme__name', 'unique_ref_no', 'bse_sip_id')
    list_filter = ('status', 'frequency', 'start_date')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('unique_ref_no', 'investor', 'scheme', 'amount', 'transaction_type', 'status', 'payment_mode', 'created_at')
    search_fields = ('unique_ref_no', 'investor__user__username', 'scheme__name', 'bse_order_id', 'investor__pan')
    list_filter = ('status', 'transaction_type', 'payment_mode', 'created_at')
