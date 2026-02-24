from rest_framework import serializers
from apps.investments.models import Order
from apps.users.models import InvestorProfile, RMProfile, DistributorProfile
from apps.products.models import Scheme

class SchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scheme
        fields = ['id', 'name', 'scheme_code']

class InvestorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = InvestorProfile
        fields = ['id', 'name', 'username']

class OrderSerializer(serializers.ModelSerializer):
    investor_name = serializers.CharField(source='investor.user.name', read_only=True)
    scheme_name = serializers.CharField(source='scheme.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'unique_ref_no', 'investor_name', 'scheme_name',
            'amount', 'status', 'status_display', 'created_at'
        ]
