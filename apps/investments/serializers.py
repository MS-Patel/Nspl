from rest_framework import serializers
from .models import Order, SIP, Mandate, Folio
from apps.products.models import Scheme
from apps.users.models import InvestorProfile
from apps.users.models import BankAccount

class OrderCreateSerializer(serializers.ModelSerializer):
    investor_id = serializers.IntegerField(write_only=True)
    scheme_id = serializers.IntegerField(write_only=True)
    target_scheme_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    folio_number = serializers.CharField(write_only=True, required=False, allow_null=True)
    mandate_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    # SIP Specific
    sip_frequency = serializers.ChoiceField(choices=SIP.FREQUENCY_CHOICES, required=False)
    sip_start_date = serializers.DateField(required=False)
    sip_installments = serializers.IntegerField(required=False)

    class Meta:
        model = Order
        fields = [
            'investor_id', 'scheme_id', 'target_scheme_id', 'folio_number', 'mandate_id',
            'transaction_type', 'amount', 'units', 'payment_mode', 'all_redeem',
            'sip_frequency', 'sip_start_date', 'sip_installments'
        ]

    def validate(self, data):
        txn_type = data.get('transaction_type')

        if txn_type == Order.SIP:
            if not data.get('sip_frequency') or not data.get('sip_start_date') or not data.get('sip_installments'):
                raise serializers.ValidationError("SIP frequency, start date, and installments are required for SIP orders.")
            if not data.get('mandate_id'):
                raise serializers.ValidationError("Mandate is required for SIP orders.")

        if txn_type == Order.SWITCH:
            if not data.get('target_scheme_id'):
                raise serializers.ValidationError("Target scheme is required for Switch orders.")

        if txn_type == Order.REDEMPTION:
             if not data.get('folio_number'):
                raise serializers.ValidationError("Folio number is required for Redemption orders.")

        return data

class OrderListSerializer(serializers.ModelSerializer):
    investor_name = serializers.CharField(source='investor.user.name', read_only=True)
    scheme_name = serializers.CharField(source='scheme.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'unique_ref_no', 'created_at', 'investor_name', 'scheme_name',
            'transaction_type', 'transaction_type_display', 'amount', 'units',
            'status', 'status_display', 'bse_remarks', 'bse_order_id'
        ]

class SIPListSerializer(serializers.ModelSerializer):
    investor_name = serializers.CharField(source='investor.user.name', read_only=True)
    scheme_name = serializers.CharField(source='scheme.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)

    class Meta:
        model = SIP
        fields = [
            'id', 'created_at', 'investor_name', 'scheme_name', 'amount',
            'frequency', 'frequency_display', 'start_date', 'end_date',
            'installments', 'status', 'status_display', 'bse_reg_no'
        ]

class MandateSerializer(serializers.ModelSerializer):
    bank_name = serializers.CharField(source='bank_account.bank_name', read_only=True)
    account_number = serializers.CharField(source='bank_account.account_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Mandate
        fields = [
            'id', 'mandate_id', 'amount_limit', 'start_date', 'end_date',
            'status', 'status_display', 'bank_name', 'account_number', 'mandate_type'
        ]

class MandateCreateSerializer(serializers.ModelSerializer):
    investor_id = serializers.IntegerField(write_only=True)
    bank_account_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Mandate
        fields = [
            'investor_id', 'bank_account_id', 'amount_limit', 'start_date', 'end_date', 'mandate_type'
        ]
