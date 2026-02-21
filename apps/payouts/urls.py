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
    path('payouts/import-list/', views.BrokerageImportListView.as_view(), name='import_list'),
]
