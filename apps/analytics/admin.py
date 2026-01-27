from django.contrib import admin
from .models import Goal, GoalMapping, CASUpload, ExternalHolding

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('name', 'investor', 'target_amount', 'target_date', 'category', 'current_value', 'achievement_percentage')
    search_fields = ('name', 'investor__user__username', 'investor__pan')
    list_filter = ('category', 'target_date')

@admin.register(GoalMapping)
class GoalMappingAdmin(admin.ModelAdmin):
    list_display = ('goal', 'holding', 'allocation_percentage')
    search_fields = ('goal__name', 'holding__scheme__name')

@admin.register(CASUpload)
class CASUploadAdmin(admin.ModelAdmin):
    list_display = ('investor', 'uploaded_by', 'status', 'uploaded_at', 'processed_at')
    search_fields = ('investor__user__username', 'investor__pan', 'uploaded_by__username')
    list_filter = ('status', 'uploaded_at')

@admin.register(ExternalHolding)
class ExternalHoldingAdmin(admin.ModelAdmin):
    list_display = ('investor', 'scheme_name', 'units', 'current_value', 'valuation_date')
    search_fields = ('investor__user__username', 'scheme_name', 'isin', 'folio_number')
    list_filter = ('valuation_date',)
