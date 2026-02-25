from django.urls import path
from . import views, api_views

app_name = 'products'
urlpatterns = [
    path('explore/', views.SchemeExplorerView.as_view(), name='scheme_explore'),
    path('schemes/', views.SchemeListView.as_view(), name='scheme_list'),
    path('schemes/<int:pk>/', views.SchemeDetailView.as_view(), name='scheme_detail'),
    path('schemes/<int:pk>/edit/', views.SchemeUpdateView.as_view(), name='scheme_edit'), # New Edit Route
    path('schemes/upload/', views.SchemeUploadView.as_view(), name='scheme_upload'),
    path('schemes/upload/sample/', views.DownloadSchemeSampleView.as_view(), name='scheme_upload_sample'),
    path('navs/upload/', views.NAVUploadView.as_view(), name='nav_upload'),
    path('navs/upload/sample/', views.DownloadNAVSampleView.as_view(), name='nav_upload_sample'),
    path('amc/', views.AMCMasterView.as_view(), name='amc_list'),
    path('amc/<int:pk>/toggle/', views.toggle_amc_status, name='amc_toggle'),
    path('amc/<int:pk>/update/', views.update_amc_name, name='amc_update'),
    path('schemes/export/master/', views.DownloadSchemeMasterReportView.as_view(), name='scheme_master_export'),

    # API Endpoints
    path('api/amc/', api_views.AMCListCreateAPIView.as_view(), name='api_amc_list'),
    path('api/amc/<int:pk>/', api_views.AMCDetailAPIView.as_view(), name='api_amc_detail'),
    path('api/schemes/', api_views.SchemeListAPIView.as_view(), name='api_scheme_list'),
    path('api/categories/', api_views.SchemeCategoryListAPIView.as_view(), name='api_category_list'),
    path('api/schemes/upload/', api_views.SchemeUploadAPIView.as_view(), name='api_scheme_upload'),
    path('api/navs/upload/', api_views.NAVUploadAPIView.as_view(), name='api_nav_upload'),
]
