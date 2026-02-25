from django.urls import path
from . import views

app_name = 'payouts'

urlpatterns = [
    path('payouts/dashboard/', views.PayoutDashboardView.as_view(), name='dashboard'),
    path('payouts/upload/', views.BrokerageUploadView.as_view(), name='upload'),
    path('payouts/list/', views.PayoutListView.as_view(), name='payout_list'),
    path('payouts/detail/<int:pk>/', views.PayoutDetailView.as_view(), name='payout_detail'),
    path('payouts/import/<int:pk>/', views.BrokerageImportDetailView.as_view(), name='import_detail'),
    path('payouts/import/<int:pk>/reprocess/', views.ReprocessImportView.as_view(), name='reprocess_import'),
    path('payouts/import/<int:pk>/export/', views.ExportPayoutReportView.as_view(), name='export_payout_report'),
    path('payouts/import/<int:pk>/export-amc/', views.ExportAMCPayoutReportView.as_view(), name='export_amc_report'),
    path('payouts/import/<int:pk>/export-transactions/', views.ExportTransactionReportView.as_view(), name='export_transaction_report'),
    path('payouts/import-list/', views.BrokerageImportListView.as_view(), name='import_list'),

    # Category Management
    path('payouts/categories/', views.DistributorCategoryListView.as_view(), name='category_list'),
    path('payouts/categories/add/', views.DistributorCategoryCreateView.as_view(), name='category_add'),
    path('payouts/categories/<int:pk>/edit/', views.DistributorCategoryUpdateView.as_view(), name='category_edit'),
    path('payouts/categories/<int:pk>/delete/', views.DistributorCategoryDeleteView.as_view(), name='category_delete'),

    # Folio Mapping
    path('payouts/folio-mappings/', views.FolioMappingListView.as_view(), name='folio_mapping_list'),
    path('payouts/folio-mappings/import/', views.FolioMappingImportView.as_view(), name='folio_mapping_import'),
]
