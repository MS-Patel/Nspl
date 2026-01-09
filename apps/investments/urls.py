from django.urls import path
from .views import OrderCreateView, OrderDetailView, InvestorFoliosView

urlpatterns = [
    path('invest/order/create/', OrderCreateView.as_view(), name='order_create'),
    path('invest/order/<int:pk>/', OrderDetailView.as_view(), name='order_detail'),
    path('invest/order/success/', OrderCreateView.as_view(), name='order_success'), # Temporary
    path('api/folios/', InvestorFoliosView.as_view(), name='api_folios'),
]
