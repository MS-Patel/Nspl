from django.urls import path
from . import views
from . import api_views
from apps.website.views import ReactAppView

app_name = 'users'

urlpatterns = [
    path('legacy/login/', views.CustomLoginView.as_view(), name='login_legacy'),
    path('login/', ReactAppView.as_view(), name='login'),
    path('users/api/auth/login/', views.APILoginView.as_view(), name='api_login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),

    # OTP Login
    path('otp/send/', views.SendOTPView.as_view(), name='send_otp'),
    path('otp/login/', views.VerifyOTPLoginView.as_view(), name='verify_otp_login'),

    # API Dashboards
    path('api/dashboard/admin/', api_views.AdminDashboardAPIView.as_view(), name='api_admin_dashboard'),
    path('api/dashboard/rm/', api_views.RMDashboardAPIView.as_view(), name='api_rm_dashboard'),
    path('api/dashboard/distributor/', api_views.DistributorDashboardAPIView.as_view(), name='api_distributor_dashboard'),
    path('api/dashboard/investor/', api_views.InvestorDashboardAPIView.as_view(), name='api_investor_dashboard'),

    # API: Investor Module
    path('api/investors/', api_views.InvestorListAPIView.as_view(), name='api_investor_list'),
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
    path('api/rms/<int:pk>/', api_views.RMDetailAPIView.as_view(), name='api_rm_detail'),
    path('api/distributors/', api_views.DistributorListCreateAPIView.as_view(), name='api_distributor_list_create'),
    path('api/distributors/<int:pk>/', api_views.DistributorDetailAPIView.as_view(), name='api_distributor_detail'),

    # API: Bulk Operations
    path('api/distributor-mapping/', api_views.DistributorMappingAPIView.as_view(), name='api_distributor_mapping'),
    path('api/distributor-selection/', api_views.DistributorSelectionListAPIView.as_view(), name='api_distributor_selection'),

    path('api/branches/', api_views.BranchListAPIView.as_view(), name='api_branch_list'),
    # User Info
    path('api/user/me/', api_views.UserMeAPIView.as_view(), name='api_user_me'),

    # Dashboards (React)
    path('dashboard/admin/', ReactAppView.as_view(), name='admin_dashboard'),
    path('dashboard/rm/', ReactAppView.as_view(), name='rm_dashboard'),
    path('dashboard/distributor/', ReactAppView.as_view(), name='distributor_dashboard'),
    path('dashboard/investor/', ReactAppView.as_view(), name='investor_dashboard'),

    # User Management
    path('users/rm/', views.RMListView.as_view(), name='rm_list'),
    path('users/rm/create/', views.RMCreateView.as_view(), name='rm_create'),
    path('users/rm/<int:pk>/update/', views.RMUpdateView.as_view(), name='rm_update'),
    path('users/rm/upload/', views.RMUploadView.as_view(), name='rm_upload'),
    path('users/rm/upload/sample/', views.DownloadRMSampleView.as_view(), name='rm_upload_sample'),

    path('users/distributor/', views.DistributorListView.as_view(), name='distributor_list'),
    path('users/distributor/create/', views.DistributorCreateView.as_view(), name='distributor_create'),
    path('users/distributor/<int:pk>/update/', views.DistributorUpdateView.as_view(), name='distributor_update'),
    path('users/distributor/upload/', views.DistributorUploadView.as_view(), name='distributor_upload'),
    path('users/distributor/upload/sample/', views.DownloadDistributorSampleView.as_view(), name='distributor_upload_sample'),

    path('users/investor/', views.InvestorListView.as_view(), name='investor_list'),
    path('users/investor/mapping/', views.DistributorMappingView.as_view(), name='distributor_mapping'),
    path('users/investor/create/', views.InvestorCreateView.as_view(), name='investor_create'),
    path('users/investor/onboard/', views.InvestorCreateView.as_view(), name='investor_onboard'), # New Wizard
    path('users/investor/<int:pk>/update/', views.InvestorUpdateView.as_view(), name='investor_update'),
    path('users/investor/<int:pk>/', views.InvestorDetailView.as_view(), name='investor_detail'),
    path('users/investor/<int:pk>/push-bse/', views.PushToBSEView.as_view(), name='push_to_bse'),
    path('users/investor/<int:pk>/fatca-upload/', views.FATCAUploadView.as_view(), name='fatca_upload'),
    path('users/investor/<int:pk>/trigger-auth/', views.TriggerNomineeAuthView.as_view(), name='trigger_nominee_auth'),
    path('users/investor/<int:pk>/opt-out-nominee/', views.OptOutNomineeView.as_view(), name='opt_out_nominee'),
    path('users/investor/<int:pk>/toggle-kyc/', views.ToggleKYCView.as_view(), name='toggle_kyc'),
    path('users/investor/upload/', views.InvestorUploadView.as_view(), name='investor_upload'),
    path('users/investor/upload/sample/', views.DownloadInvestorSampleView.as_view(), name='investor_upload_sample'),

    # Profile & Settings
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('password-change/', views.UserPasswordChangeView.as_view(), name='password_change'),
    path('password-reset/', views.UserPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.UserPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.UserPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.UserPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
