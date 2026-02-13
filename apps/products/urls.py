from django.urls import path
from . import views

app_name = 'products'
urlpatterns = [
    path('schemes/', views.SchemeListView.as_view(), name='scheme_list'),
    path('schemes/<int:pk>/', views.SchemeDetailView.as_view(), name='scheme_detail'),
    path('schemes/upload/', views.SchemeUploadView.as_view(), name='scheme_upload'),
    path('schemes/upload/sample/', views.DownloadSchemeSampleView.as_view(), name='scheme_upload_sample'),
    path('navs/upload/', views.NAVUploadView.as_view(), name='nav_upload'),
    path('navs/upload/sample/', views.DownloadNAVSampleView.as_view(), name='nav_upload_sample'),
]
