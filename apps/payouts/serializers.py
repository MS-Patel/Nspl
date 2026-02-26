from rest_framework import serializers
from .models import BrokerageImport

class BrokerageImportSerializer(serializers.ModelSerializer):
    total_brokerage = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)

    class Meta:
        model = BrokerageImport
        fields = ['id', 'month', 'year', 'uploaded_at', 'status', 'total_brokerage']
