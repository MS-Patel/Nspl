from django.urls import path
from . import views

app_name = 'products'
urlpatterns = [
    path('schemes/', views.SchemeListView.as_view(), name='scheme_list'),
]
