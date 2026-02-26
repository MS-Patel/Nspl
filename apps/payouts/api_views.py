from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Sum
from .models import BrokerageImport
from .serializers import BrokerageImportSerializer

class BrokerageImportListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = BrokerageImportSerializer

    def get_queryset(self):
        return BrokerageImport.objects.annotate(
            total_brokerage=Sum('payouts__gross_brokerage')
        ).order_by('-year', '-month')
