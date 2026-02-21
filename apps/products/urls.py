from django.urls import path
from . import views

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
]
