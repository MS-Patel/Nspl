from django.urls import path
from . import views
from . import api_views
from apps.website.views import ReactAppView

app_name = 'users'

urlpatterns = [
    path('legacy/login/', views.CustomLoginView.as_view(), name='login_legacy'),
    path('login/', ReactAppView.as_view(), name='login'),
    path('users/api/auth/login/', views.APILoginView.as_view(), name='api_login'),
    path('api/auth/password-reset/request/', api_views.RequestPasswordResetAPIView.as_view(), name='api_password_reset_request'),
    path('api/auth/password-reset/confirm/', api_views.ResetPasswordConfirmAPIView.as_view(), name='api_password_reset_confirm'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),

    # OTP Login
    path('otp/send/', views.SendOTPView.as_view(), name='send_otp'),
    path('otp/login/', views.VerifyOTPLoginView.as_view(), name='verify_otp_login'),

    # API Dashboards
    path('api/dashboard/admin/', api_views.AdminDashboardAPIView.as_view(), name='api_admin_dashboard'),
    path('api/dashboard/rm/', api_views.RMDashboardAPIView.as_view(), name='api_rm_dashboard'),
    path('api/dashboard/distributor/', api_views.DistributorDashboardAPIView.as_view(), name='api_distributor_dashboard'),
    path('api/dashboard/investor/', api_views.InvestorDashboardAPIView.as_view(), name='api_investor_dashboard'),

    # API: Portfolio & Holdings
    path('api/portfolio/analytics/', api_views.PortfolioAnalyticsAPIView.as_view(), name='api_portfolio_analytics'),
    path('api/holdings/', api_views.HoldingListAPIView.as_view(), name='api_holding_list'),

    # API: Investor Module
    path('api/investors/', api_views.InvestorListAPIView.as_view(), name='api_investor_list'),
    path('api/investors/upload/', api_views.InvestorUploadAPIView.as_view(), name='api_investor_upload'),
    path('api/investors/upload/sample/', api_views.DownloadInvestorSampleAPIView.as_view(), name='api_investor_upload_sample'),
    path('api/investors/onboard/', api_views.InvestorCreateAPIView.as_view(), name='api_investor_create'),
    path('api/investors/<int:pk>/', api_views.InvestorDetailAPIView.as_view(), name='api_investor_detail'),

    # API: Nested Resources
    path('api/investors/<int:investor_id>/bank-accounts/', api_views.BankAccountListCreateAPIView.as_view(), name='api_investor_bank_list_create'),
    path('api/bank-accounts/<int:pk>/', api_views.BankAccountDetailAPIView.as_view(), name='api_bank_detail'),
    path('api/investors/<int:investor_id>/nominees/', api_views.NomineeListCreateAPIView.as_view(), name='api_investor_nominee_list_create'),
    path('api/nominees/<int:pk>/', api_views.NomineeDetailAPIView.as_view(), name='api_nominee_detail'),
    path('api/investors/<int:investor_id>/documents/', api_views.DocumentListCreateAPIView.as_view(), name='api_investor_document_list_create'),
    path('api/documents/<int:pk>/', api_views.DocumentDetailAPIView.as_view(), name='api_document_detail'),

    # API: BSE & Compliance Actions
    path('api/investors/<int:pk>/push-bse/', api_views.PushToBSEAPIView.as_view(), name='api_push_to_bse'),
    path('api/investors/<int:pk>/trigger-auth/', api_views.TriggerAuthAPIView.as_view(), name='api_trigger_auth'),
    path('api/investors/<int:pk>/toggle-kyc/', api_views.ToggleKYCAPIView.as_view(), name='api_toggle_kyc'),
    path('api/investors/<int:pk>/fatca-upload/', api_views.FATCAUploadAPIView.as_view(), name='api_fatca_upload'),

    # API: RM & Distributor Management
    path('api/rms/', api_views.RMListCreateAPIView.as_view(), name='api_rm_list_create'),
    path('api/rms/upload/', api_views.RMUploadAPIView.as_view(), name='api_rm_upload'),
    path('api/rms/upload/sample/', api_views.DownloadRMSampleAPIView.as_view(), name='api_rm_upload_sample'),
    path('api/rms/<int:pk>/', api_views.RMDetailAPIView.as_view(), name='api_rm_detail'),
    path('api/distributors/', api_views.DistributorListCreateAPIView.as_view(), name='api_distributor_list_create'),
    path('api/distributors/upload/', api_views.DistributorUploadAPIView.as_view(), name='api_distributor_upload'),
    path('api/distributors/upload/sample/', api_views.DownloadDistributorSampleAPIView.as_view(), name='api_distributor_upload_sample'),
    path('api/distributors/<int:pk>/', api_views.DistributorDetailAPIView.as_view(), name='api_distributor_detail'),

    # API: Bulk Operations
    path('api/distributor-mapping/', api_views.DistributorMappingAPIView.as_view(), name='api_distributor_mapping'),
    path('api/distributor-selection/', api_views.DistributorSelectionListAPIView.as_view(), name='api_distributor_selection'),

    path('api/branches/', api_views.BranchListAPIView.as_view(), name='api_branch_list'),
    # User Info
    path('api/user/me/', api_views.UserMeAPIView.as_view(), name='api_user_me'),
    path('api/user/profile/', api_views.UserProfileAPIView.as_view(), name='api_user_profile'),
    path('api/user/password-change/', api_views.PasswordChangeAPIView.as_view(), name='api_password_change'),

    # Dashboards (React)
    path('dashboard/admin/', ReactAppView.as_view(), name='admin_dashboard'),
    path('dashboard/rm/', ReactAppView.as_view(), name='rm_dashboard'),
    path('dashboard/distributor/', ReactAppView.as_view(), name='distributor_dashboard'),
    path('dashboard/investor/', ReactAppView.as_view(), name='investor_dashboard'),

]
