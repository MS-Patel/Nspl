from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.investments.models import Order, Mandate
from apps.users.models import InvestorProfile, RMProfile, DistributorProfile, BankAccount, Nominee, Document, Branch
from apps.products.models import Scheme

User = get_user_model()

class SchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scheme
        fields = ['id', 'name', 'scheme_code']

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['id', 'name', 'code']

class BankAccountSerializer(serializers.ModelSerializer):
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)

    class Meta:
        model = BankAccount
        fields = [
            'id', 'bank_name', 'account_number', 'ifsc_code', 'account_type',
            'account_type_display', 'branch_name', 'is_default', 'bse_index'
        ]

class NomineeSerializer(serializers.ModelSerializer):
    relationship_display = serializers.CharField(source='get_relationship_display', read_only=True)
    id_type_display = serializers.CharField(source='get_id_type_display', read_only=True)

    class Meta:
        model = Nominee
        fields = [
            'id', 'name', 'relationship', 'relationship_display', 'percentage',
            'date_of_birth', 'guardian_name', 'guardian_pan', 'pan',
            'address_1', 'address_2', 'address_3', 'city', 'state', 'pincode',
            'country', 'mobile', 'email', 'id_type', 'id_type_display', 'id_number'
        ]

class DocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ['id', 'document_type', 'document_type_display', 'file_url', 'uploaded_at', 'description']

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None

class MandateSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    mandate_type_display = serializers.CharField(source='get_mandate_type_display', read_only=True)
    bank_account_number = serializers.CharField(source='bank_account.account_number', read_only=True)
    bank_name = serializers.CharField(source='bank_account.bank_name', read_only=True)

    class Meta:
        model = Mandate
        fields = [
            'id', 'mandate_id', 'mandate_type', 'mandate_type_display',
            'amount_limit', 'start_date', 'end_date', 'status', 'status_display',
            'bank_account', 'bank_account_number', 'bank_name',
            'created_at', 'updated_at', 'is_bse_submitted'
        ]

class InvestorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    distributor_name = serializers.SerializerMethodField()
    rm_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    # Detail fields
    bank_accounts = BankAccountSerializer(many=True, read_only=True)
    nominees = NomineeSerializer(many=True, read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    mandates = MandateSerializer(many=True, read_only=True)

    # Status Displays
    tax_status_display = serializers.CharField(source='get_tax_status_display', read_only=True)
    occupation_display = serializers.CharField(source='get_occupation_display', read_only=True)
    holding_nature_display = serializers.CharField(source='get_holding_nature_display', read_only=True)
    kyc_type_display = serializers.CharField(source='get_kyc_type_display', read_only=True)
    nominee_auth_status_display = serializers.CharField(source='get_nominee_auth_status_display', read_only=True)

    # FATCA Displays
    source_of_wealth_display = serializers.CharField(source='get_source_of_wealth_display', read_only=True)
    income_slab_display = serializers.CharField(source='get_income_slab_display', read_only=True)
    pep_status_display = serializers.CharField(source='get_pep_status_display', read_only=True)

    class Meta:
        model = InvestorProfile
        fields = [
            'id', 'name', 'username', 'email', 'pan', 'mobile',
            'distributor_name', 'rm_name', 'status',
            'dob', 'gender', 'address_1', 'address_2', 'address_3',
            'city', 'state', 'pincode', 'country',

            # Foreign Address
            'foreign_address_1', 'foreign_address_2', 'foreign_address_3',
            'foreign_city', 'foreign_state', 'foreign_pincode', 'foreign_country',
            'foreign_resi_phone', 'foreign_off_phone',

            # Joint Holders
            'second_applicant_name', 'second_applicant_pan', 'second_applicant_dob',
            'third_applicant_name', 'third_applicant_pan', 'third_applicant_dob',

            # FATCA
            'place_of_birth', 'country_of_birth',
            'source_of_wealth', 'source_of_wealth_display',
            'income_slab', 'income_slab_display',
            'pep_status', 'pep_status_display',
            'exemption_code',

            'tax_status', 'tax_status_display',
            'occupation', 'occupation_display',
            'holding_nature', 'holding_nature_display',
            'kyc_type', 'kyc_type_display',
            'nominee_auth_status', 'nominee_auth_status_display',
            'ucc_code', 'bse_remarks', 'last_verified_at', 'kyc_status',

            'bank_accounts', 'nominees', 'documents', 'mandates'
        ]

    def get_distributor_name(self, obj):
        if obj.distributor and obj.distributor.user:
            return obj.distributor.user.name or obj.distributor.user.username
        return None

    def get_rm_name(self, obj):
        if obj.rm and obj.rm.user:
            return obj.rm.user.name or obj.rm.user.username
        return None

    def get_status(self, obj):
        return 'Active' if obj.user.is_active else 'Inactive'

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

class InvestorCreateSerializer(serializers.ModelSerializer):
    firstname = serializers.CharField(write_only=True)
    middlename = serializers.CharField(write_only=True, required=False, allow_blank=True)
    lastname = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)

    bank_accounts = BankAccountSerializer(many=True, required=False)
    nominees = NomineeSerializer(many=True, required=False)

    class Meta:
        model = InvestorProfile
        fields = [
            'id', 'firstname', 'middlename', 'lastname', 'email', 'pan', 'mobile',
            'dob', 'gender', 'occupation', 'tax_status', 'holding_nature',
            'bank_accounts', 'nominees'
        ]

    def create(self, validated_data):
        bank_accounts_data = validated_data.pop('bank_accounts', [])
        nominees_data = validated_data.pop('nominees', [])

        # User Fields
        firstname = validated_data.pop('firstname')
        middlename = validated_data.pop('middlename', '')
        lastname = validated_data.pop('lastname')
        email = validated_data.pop('email')
        pan = validated_data.get('pan')

        fullname = f"{firstname} {middlename} {lastname}".replace('  ', ' ').strip()

        # Create User
        user = User.objects.create_user(
            username=pan,
            email=email,
            password=pan, # Default password is PAN
            name=fullname,
            user_type=User.Types.INVESTOR
        )

        # Create Investor Profile
        validated_data['user'] = user
        validated_data['kyc_status'] = True # Mock KYC

        # Determine Hierarchy (from request user context if possible, but serializer doesn't have request easily unless passed)
        # For now, default logic or handled in View?
        # Ideally view handles permissions and assignment.
        # But we need to save the profile first.

        investor = InvestorProfile.objects.create(**validated_data)

        # Determine Hierarchy based on logged in user (Accessed via context)
        request = self.context.get('request')
        if request and request.user:
            user = request.user
            if user.user_type == User.Types.DISTRIBUTOR:
                investor.distributor = user.distributor_profile
                investor.rm = user.distributor_profile.rm
                if investor.rm:
                    investor.branch = investor.rm.branch
            elif user.user_type == User.Types.RM:
                investor.rm = user.rm_profile
                if investor.rm:
                    investor.branch = investor.rm.branch

            investor.save()

        # Create Nested Objects
        for bank_data in bank_accounts_data:
            BankAccount.objects.create(investor=investor, **bank_data)

        for nominee_data in nominees_data:
            Nominee.objects.create(investor=investor, **nominee_data)

        return investor

class DistributorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = DistributorProfile
        fields = ['id', 'name', 'arn_number', 'broker_code']

# --- New Serializers ---

class RMSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = RMProfile
        fields = [
            'id', 'name', 'username', 'email', 'employee_code', 'branch', 'branch_name',
            'mobile', 'alternate_mobile', 'alternate_email',
            'address', 'city', 'state', 'pincode', 'country',
            'dob', 'gstin', 'is_active',
            'bank_name', 'account_number', 'ifsc_code'
        ]

class RMCreateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    username = serializers.CharField(write_only=True) # Usually employee code or email, but let's make it explicit

    class Meta:
        model = RMProfile
        fields = [
            'name', 'email', 'password', 'username', 'employee_code', 'branch',
            'mobile', 'alternate_mobile', 'alternate_email',
            'address', 'city', 'state', 'pincode',
            'dob', 'gstin',
            'bank_name', 'account_number', 'ifsc_code'
        ]

    def create(self, validated_data):
        name = validated_data.pop('name')
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        username = validated_data.pop('username')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            name=name,
            user_type=User.Types.RM
        )

        rm_profile = RMProfile.objects.create(user=user, **validated_data)
        return rm_profile

    def update(self, instance, validated_data):
        # Handle user fields separately if provided
        user_data = {}
        if 'name' in validated_data:
            user_data['name'] = validated_data.pop('name')
        if 'email' in validated_data:
            user_data['email'] = validated_data.pop('email')
        # We generally don't update password/username here for simplicity, or we can add logic.

        if user_data:
            for attr, value in user_data.items():
                setattr(instance.user, attr, value)
            instance.user.save()

        return super().update(instance, validated_data)


class DistributorProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    rm_name = serializers.CharField(source='rm.user.name', read_only=True, allow_null=True)

    class Meta:
        model = DistributorProfile
        fields = [
            'id', 'name', 'username', 'email', 'arn_number', 'broker_code',
            'rm', 'rm_name', 'parent',
            'mobile', 'alternate_mobile', 'alternate_email',
            'address', 'city', 'state', 'pincode', 'country',
            'dob', 'gstin', 'pan', 'is_active',
            'bank_name', 'account_number', 'ifsc_code'
        ]

class DistributorCreateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    username = serializers.CharField(write_only=True) # Login ID

    class Meta:
        model = DistributorProfile
        fields = [
            'name', 'email', 'password', 'username', 'arn_number',
            'rm', 'parent',
            'mobile', 'alternate_mobile', 'alternate_email',
            'address', 'city', 'state', 'pincode',
            'dob', 'gstin', 'pan',
            'bank_name', 'account_number', 'ifsc_code'
        ]

    def create(self, validated_data):
        name = validated_data.pop('name')
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        username = validated_data.pop('username')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            name=name,
            user_type=User.Types.DISTRIBUTOR
        )

        distributor = DistributorProfile.objects.create(user=user, **validated_data)
        return distributor

    def update(self, instance, validated_data):
        user_data = {}
        if 'name' in validated_data:
            user_data['name'] = validated_data.pop('name')
        if 'email' in validated_data:
            user_data['email'] = validated_data.pop('email')

        if user_data:
            for attr, value in user_data.items():
                setattr(instance.user, attr, value)
            instance.user.save()

        return super().update(instance, validated_data)
