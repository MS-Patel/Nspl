from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.ReportDashboardView.as_view(), name='dashboard'),
    path('investors/', views.InvestorReportView.as_view(), name='investor_report'),
    path('transactions/', views.TransactionReportView.as_view(), name='transaction_report'),
    path('masters/<str:type>/', views.MasterReportView.as_view(), name='master_report'),
    path('order-status/', views.OrderStatusReportView.as_view(), name='order_status_report'),
    path('allotment/', views.AllotmentReportView.as_view(), name='allotment_report'),
    path('redemption/', views.RedemptionReportView.as_view(), name='redemption_report'),
]
