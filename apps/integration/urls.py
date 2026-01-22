from django.urls import path
from . import views

app_name = 'integration'

urlpatterns = [
    path('tools/pan-check/', views.BSEPanCheckToolView.as_view(), name='pan_check_tool'),
    path('api/pan-check/', views.CheckPANStatusView.as_view(), name='api_pan_check'),
]
