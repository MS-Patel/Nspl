from django.urls import path
from . import views

app_name = 'investments'

urlpatterns = [
    path('order/create/', views.order_create, name='order_create'),
    path('order/list/', views.order_list, name='order_list'),
    path('holdings/', views.HoldingListView.as_view(), name='holding_list'),
    path('folio/<path:folio_number>/', views.FolioDetailView.as_view(), name='folio_detail'),
    path('redemption/create/<int:holding_id>/', views.RedemptionCreateView.as_view(), name='redemption_create'),
    path('mandate/create/', views.MandateCreateView.as_view(), name='mandate_create'),
    path('mandate/<int:pk>/auth/', views.mandate_authorize, name='mandate_auth'),
    path('api/folios/', views.get_investor_folios, name='api_folios'),
    path('api/metadata/', views.get_order_metadata, name='api_order_metadata'),
]
