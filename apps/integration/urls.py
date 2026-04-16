from django.urls import path
from . import views

app_name = 'integration'

urlpatterns = [
    path('tools/pan-check/', views.BSEPanCheckToolView.as_view(), name='pan_check_tool'),
    path('tools/ndml-kyc-registration/', views.NDMLRegistrationToolView.as_view(), name='ndml_kyc_registration_tool'),
    path('api/pan-check/', views.CheckPANStatusView.as_view(), name='api_pan_check'),
    path('api/bank-details/', views.GetBankDetailsView.as_view(), name='api_bank_details'),
    path('api/ndml/register/', views.NDMLRegistrationView.as_view(), name='api_ndml_register'),
    path('api/ndml/inquiry/', views.NDMLInquiryView.as_view(), name='api_ndml_inquiry'),
    path('api/ndml/download/', views.NDMLDownloadView.as_view(), name='api_ndml_download'),
]
