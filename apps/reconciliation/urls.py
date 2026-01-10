from django.urls import path
from . import views

urlpatterns = [
    path('reconciliation/upload/', views.upload_rta_file, name='rta_upload'),
]
