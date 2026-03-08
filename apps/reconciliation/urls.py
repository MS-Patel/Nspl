from django.urls import path
from . import views

app_name = 'reconciliation'
urlpatterns = [
    path('reconciliation/upload/', views.upload_rta_file, name='rta_upload'),
    path('reconciliation/failed-records/', views.FailedRTARecordListView.as_view(), name='failed_records'),
    path('reconciliation/failed-records/retry/', views.RetryFailedRTARecordView.as_view(), name='retry_failed_records'),
    path('reconciliation/failed-records/retry/<int:pk>/', views.RetryFailedRTARecordView.as_view(), name='retry_failed_record'),
]
