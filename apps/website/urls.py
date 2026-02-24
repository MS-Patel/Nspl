from django.urls import path, re_path
from . import views

app_name = 'website'

urlpatterns = [
    re_path(r'^(?!media/|static/).*$', views.ReactAppView.as_view(), name='react_app'),
]
