from django.urls import path
from . import views

urlpatterns = [
    path('order/create/', views.order_create, name='order_create'),
    path('order/list/', views.order_list, name='order_list'),
    path('api/folios/', views.get_investor_folios, name='api_folios'),
    path('api/metadata/', views.get_order_metadata, name='api_order_metadata'),
]
