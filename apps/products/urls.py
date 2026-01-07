from django.urls import path
from . import views

urlpatterns = [
    path('schemes/', views.SchemeListView.as_view(), name='scheme_list'),
]
