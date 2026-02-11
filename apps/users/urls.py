from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),

    # Dashboards
    path('dashboard/admin/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('dashboard/rm/', views.RMDashboardView.as_view(), name='rm_dashboard'),
    path('dashboard/distributor/', views.DistributorDashboardView.as_view(), name='distributor_dashboard'),
    path('dashboard/investor/', views.InvestorDashboardView.as_view(), name='investor_dashboard'),

    # User Management
    path('users/rm/', views.RMListView.as_view(), name='rm_list'),
    path('users/rm/create/', views.RMCreateView.as_view(), name='rm_create'),

    path('users/distributor/', views.DistributorListView.as_view(), name='distributor_list'),
    path('users/distributor/create/', views.DistributorCreateView.as_view(), name='distributor_create'),
    path('users/distributor/upload/', views.DistributorUploadView.as_view(), name='distributor_upload'),

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
]
