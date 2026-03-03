from django.urls import path
from . import views

app_name = 'investments'

urlpatterns = [
    path('order/create/', views.order_create, name='order_create'),
    path('order/list/', views.order_list, name='order_list'),

    # Points to Investor List now
    path('holdings/', views.PortfolioInvestorListView.as_view(), name='holding_list'),

    # New: Investor Portfolio Dashboard
    path('portfolio/<int:investor_id>/', views.InvestorPortfolioView.as_view(), name='investor_portfolio'),

    # Reports
    path('portfolio/<int:investor_id>/export/wealth-report/', views.ExportWealthReportView.as_view(), name='export_wealth_report'),
    path('portfolio/<int:investor_id>/export/pl-report/', views.ExportPLReportView.as_view(), name='export_pl_report'),
    path('portfolio/<int:investor_id>/export/capital-gain/', views.ExportCapitalGainReportView.as_view(), name='export_capital_gain'),
    path('portfolio/<int:investor_id>/export/transaction-statement/', views.ExportTransactionStatementView.as_view(), name='export_transaction_statement'),

    path('folio/<path:folio_number>/', views.FolioDetailView.as_view(), name='folio_detail'),
    path('redemption/create/<int:holding_id>/', views.RedemptionCreateView.as_view(), name='redemption_create'),
    path('mandate/create/', views.MandateCreateView.as_view(), name='mandate_create'),
    path('mandate/<int:pk>/retry/', views.MandateRetryView.as_view(), name='mandate_retry'),
    path('mandate/<int:pk>/auth/', views.mandate_authorize, name='mandate_auth'),
    path('api/folios/', views.get_investor_folios, name='api_folios'),
    path('api/metadata/', views.get_order_metadata, name='api_order_metadata'),
]
