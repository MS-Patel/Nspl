from rest_framework import serializers
from .models import AMC, Scheme, SchemeCategory

class AMCSerializer(serializers.ModelSerializer):
    class Meta:
        model = AMC
        fields = ['id', 'name', 'code', 'is_active']

class SchemeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SchemeCategory
        fields = ['id', 'name', 'code']

class SchemeSerializer(serializers.ModelSerializer):
    amc_name = serializers.CharField(source='amc.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Scheme
        fields = [
            'id', 'name', 'scheme_code', 'isin',
            'amc', 'amc_name',
            'category', 'category_name',
            'scheme_type', 'scheme_plan',
            'min_purchase_amount', 'purchase_allowed',
            'is_sip_allowed', 'riskometer'
        ]
