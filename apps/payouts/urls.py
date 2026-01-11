from django.urls import path
from . import views

urlpatterns = [
    path('payouts/rules/', views.CommissionRuleListView.as_view(), name='payout_rule_list'),
    path('payouts/rules/create/', views.CommissionRuleCreateView.as_view(), name='payout_rule_create'),
    path('payouts/rules/<int:pk>/update/', views.CommissionRuleUpdateView.as_view(), name='payout_rule_update'),
]
