from django.urls import path
from . import views
from . import api_views

app_name = 'investments'

urlpatterns = [
    # Points to Investor List now
    path('holdings/', views.PortfolioInvestorListView.as_view(), name='holding_list'),

    # New: Investor Portfolio Dashboard
    path('portfolio/<int:investor_id>/', views.InvestorPortfolioView.as_view(), name='investor_portfolio'),

    path('folio/<path:folio_number>/', views.FolioDetailView.as_view(), name='folio_detail'),
    # mandate/create/ Removed (Legacy)
    path('mandate/<int:pk>/retry/', views.MandateRetryView.as_view(), name='mandate_retry'),
    path('mandate/<int:pk>/auth/', views.mandate_authorize, name='mandate_auth'),

    # Helper APIs (Used by jQuery/Vanilla JS)
    path('api/folios/', views.get_investor_folios, name='api_folios'),
    path('api/metadata/', views.get_order_metadata, name='api_order_metadata'),

    # React API Endpoints
    path('api/orders/create/', api_views.OrderCreateAPIView.as_view(), name='api_order_create'),
    path('api/orders/', api_views.OrderListAPIView.as_view(), name='api_order_list'),
    path('api/sips/', api_views.SIPListAPIView.as_view(), name='api_sip_list'),
    path('api/sips/<int:pk>/cancel/', api_views.SIPCancelAPIView.as_view(), name='api_sip_cancel'),
    path('api/mandates/', api_views.MandateListAPIView.as_view(), name='api_mandate_list'),
    path('api/mandates/create/', api_views.MandateCreateAPIView.as_view(), name='api_mandate_create'),
]
