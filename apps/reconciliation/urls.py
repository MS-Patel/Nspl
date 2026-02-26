from django.urls import path
from . import views
from . import api_views

app_name = 'reconciliation'
urlpatterns = [
    path('reconciliation/upload/', views.upload_rta_file, name='rta_upload'),
    path('api/reconciliation/upload/', api_views.ReconciliationAPIView.as_view(), name='api_reconciliation_upload'),
]
