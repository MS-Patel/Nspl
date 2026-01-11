from django.urls import path
from . import views

app_name = 'reconciliation'
urlpatterns = [
    path('reconciliation/upload/', views.upload_rta_file, name='rta_upload'),
]
