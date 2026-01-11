from django.urls import path
from . import views

app_name = 'payouts'
urlpatterns = [
    # Commission Rules (Admin)
    path('payouts/rules/', views.CommissionRuleListView.as_view(), name='payout_rule_list'),
    path('payouts/rules/create/', views.CommissionRuleCreateView.as_view(), name='payout_rule_create'),
    path('payouts/rules/<int:pk>/update/', views.CommissionRuleUpdateView.as_view(), name='payout_rule_update'),

    # Payouts (Distributor)
    path('payouts/', views.PayoutListView.as_view(), name='payout_list'),
    path('payouts/<int:pk>/', views.PayoutDetailView.as_view(), name='payout_detail'),
    path('payouts/<int:pk>/export/', views.PayoutExportView.as_view(), name='payout_export'),
]
