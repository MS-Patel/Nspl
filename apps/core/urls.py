from django.urls import path
from .views import maintenance_view

app_name = 'core'

urlpatterns = [
    path('maintenance/', maintenance_view, name='maintenance'),
]