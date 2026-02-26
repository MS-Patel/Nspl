from rest_framework.views import APIView
from rest_framework import generics, filters, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import Sum, Q
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import RMProfile, DistributorProfile, InvestorProfile, BankAccount, Nominee, Document, Branch
from apps.reconciliation.models import Holding
from apps.investments.models import Order, SIP
from .serializers import (
    OrderSerializer, InvestorSerializer, InvestorCreateSerializer,
    BankAccountSerializer, NomineeSerializer, DocumentSerializer, DistributorSerializer,
    RMSerializer, RMCreateSerializer, DistributorProfileSerializer, DistributorCreateSerializer,
    BranchSerializer
)
from apps.reconciliation.utils.valuation import calculate_portfolio_valuation
from apps.integration.sync_utils import sync_pending_orders, sync_sip_child_orders, sync_pending_mandates
from apps.users.services import validate_investor_for_bse
from apps.integration.bse_client import BSEStarMFClient
from apps.integration.utils import map_investor_to_bse_param_string
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from .utils.parsers import import_rms_from_file, import_distributors_from_file, import_investors_from_file
from apps.core.utils.excel_generator import create_excel_sample_file
from apps.core.utils.sample_headers import (
    RM_HEADERS, RM_CHOICES,
    DISTRIBUTOR_HEADERS, DISTRIBUTOR_CHOICES,
    INVESTOR_HEADERS, INVESTOR_CHOICES
)
import logging
import json
import os
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str

User = get_user_model()
logger = logging.getLogger(__name__)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class AdminDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.user_type != User.Types.ADMIN:
            return Response({'error': 'Permission denied'}, status=403)

        # 1. Counts
        rm_count = RMProfile.objects.count()
        distributor_count = DistributorProfile.objects.count()
        investor_count = InvestorProfile.objects.count()

        # 2. Total AUM
        aum_agg = Holding.objects.aggregate(total_aum=Sum('current_value'))
        total_aum = aum_agg['total_aum'] or 0

        # 3. Recent Activity
        recent_orders = Order.objects.select_related('investor__user', 'scheme').order_by('-created_at')[:10]
        recent_orders_data = OrderSerializer(recent_orders, many=True).data

        return Response({
            'rm_count': rm_count,
            'distributor_count': distributor_count,
            'investor_count': investor_count,
            'total_aum': total_aum,
            'recent_orders': recent_orders_data
        })

class RMDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.user_type != User.Types.RM:
             return Response({'error': 'Permission denied'}, status=403)

        user = request.user

        # 1. Distributors
        distributors = DistributorProfile.objects.filter(rm__user=user)
        distributor_count = distributors.count()

        # 2. Investors
        investors = InvestorProfile.objects.filter(
            Q(distributor__rm__user=user) | Q(rm__user=user)
        )
        investor_count = investors.count()

        # 3. Total AUM
        aum_agg = Holding.objects.filter(investor__in=investors).aggregate(total_aum=Sum('current_value'))
        total_aum = aum_agg['total_aum'] or 0

        # 4. Recent Orders
        recent_orders = Order.objects.filter(investor__in=investors).select_related('investor__user', 'scheme').order_by('-created_at')[:5]
        recent_orders_data = OrderSerializer(recent_orders, many=True).data

        return Response({
            'distributor_count': distributor_count,
            'investor_count': investor_count,
            'total_aum': total_aum,
            'recent_orders': recent_orders_data
        })

class DistributorDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.user_type != User.Types.DISTRIBUTOR:
             return Response({'error': 'Permission denied'}, status=403)

        user = request.user

        # 1. Investors
        investors = InvestorProfile.objects.filter(distributor__user=user)
        investor_count = investors.count()

        # 2. AUM
        aum_agg = Holding.objects.filter(investor__in=investors).aggregate(total_aum=Sum('current_value'))
        total_aum = aum_agg['total_aum'] or 0

        # 3. Active SIPs
        active_sip_count = SIP.objects.filter(investor__in=investors, status='ACTIVE').count()

        # 4. Recent Orders
        recent_orders = Order.objects.filter(investor__in=investors).select_related('investor__user', 'scheme').order_by('-created_at')[:5]
        recent_orders_data = OrderSerializer(recent_orders, many=True).data

        return Response({
            'investor_count': investor_count,
            'total_aum': total_aum,
            'active_sip_count': active_sip_count,
            'recent_orders': recent_orders_data
        })

class InvestorDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Allow Admin to view any investor dashboard? For now, stick to self.
        if request.user.user_type != User.Types.INVESTOR:
             return Response({'error': 'Permission denied'}, status=403)

        user = request.user
        investor_profile = None

        try:
            investor_profile = user.investor_profile

            # Sync
            try:
                sync_sip_child_orders(user=user, investor=investor_profile)
                sync_pending_orders(user=user, investor=investor_profile)
            except Exception as e:
                logger.error(f"Sync failed for investor {user.username}: {e}")

        except InvestorProfile.DoesNotExist:
            pass

        valuation_data = {}

        if investor_profile:
            valuation_data = calculate_portfolio_valuation(investor_profile)

        return Response({
            'valuation': valuation_data
        })

class UserMeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            'username': user.username,
            'name': user.name,
            'email': user.email,
            'role': user.user_type,
            'id': user.id
        }
        if hasattr(user, 'investor_profile'):
            data['investor_id'] = user.investor_profile.id
        return Response(data)

# --- Investor Module API Views ---

class InvestorListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InvestorSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__name', 'pan', 'user__email']

    def get_queryset(self):
        user = self.request.user
        qs = InvestorProfile.objects.select_related(
            'user', 'distributor', 'distributor__user', 'rm', 'rm__user'
        ).prefetch_related(
            'bank_accounts', 'nominees', 'documents'
        ).order_by('-id')

        if user.user_type == User.Types.DISTRIBUTOR:
            qs = qs.filter(distributor__user=user)
        elif user.user_type == User.Types.RM:
            # RM sees investors where (distributor.rm == self) OR (rm == self [Direct])
            qs = qs.filter(Q(distributor__rm__user=user) | Q(rm__user=user))
        elif user.user_type == User.Types.ADMIN:
            pass
        else:
            return qs.none()

        # Filtering
        is_offline = self.request.query_params.get('is_offline')
        if is_offline:
            qs = qs.filter(is_offline=is_offline.lower() == 'true')

        status = self.request.query_params.get('status')
        if status:
            is_active = status.lower() == 'active'
            qs = qs.filter(user__is_active=is_active)

        return qs

class DistributorSelectionListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DistributorSerializer

    def get_queryset(self):
        user = self.request.user
        if user.user_type == User.Types.ADMIN:
            return DistributorProfile.objects.all().select_related('user')
        elif user.user_type == User.Types.RM:
            return DistributorProfile.objects.filter(rm__user=user).select_related('user')
        return DistributorProfile.objects.none()

class InvestorCreateAPIView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InvestorCreateSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            serializer.save()

class InvestorDetailAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InvestorSerializer
    queryset = InvestorProfile.objects.all()

    def get_object(self):
        obj = super().get_object()
        user = self.request.user

        # Check permissions
        has_access = False
        if user.user_type == User.Types.ADMIN:
            has_access = True
        elif user.user_type == User.Types.DISTRIBUTOR:
            if obj.distributor and obj.distributor.user == user:
                has_access = True
        elif user.user_type == User.Types.RM:
             if (obj.rm and obj.rm.user == user) or (obj.distributor and obj.distributor.rm and obj.distributor.rm.user == user):
                 has_access = True
        elif user.user_type == User.Types.INVESTOR:
             if obj.user == user:
                 has_access = True

        if not has_access:
            self.permission_denied(self.request, message="You do not have permission to view this investor.")

        # Sync Mandates & Orders on Retrieve
        if self.request.method == 'GET':
             try:
                sync_pending_mandates(user=user, investor=obj)
                sync_pending_orders(user=user, investor=obj)
             except Exception as e:
                logger.error(f"Sync failed in InvestorDetailAPIView: {e}")

        return obj

# --- Nested Resources ---

class InvestorNestedMixin:
    """
    Mixin to restrict access to nested resources (Bank, Nominee, Document)
    based on the user's relationship with the parent InvestorProfile.
    """
    def check_investor_permission(self, investor):
        user = self.request.user
        has_access = False
        if user.user_type == User.Types.ADMIN:
            has_access = True
        elif user.user_type == User.Types.DISTRIBUTOR:
            if investor.distributor and investor.distributor.user == user:
                has_access = True
        elif user.user_type == User.Types.RM:
             if (investor.rm and investor.rm.user == user) or \
                (investor.distributor and investor.distributor.rm and investor.distributor.rm.user == user):
                 has_access = True
        elif user.user_type == User.Types.INVESTOR:
             if investor.user == user:
                 has_access = True

        if not has_access:
            self.permission_denied(self.request, message="You do not have permission to access this investor's resources.")

class BankAccountListCreateAPIView(InvestorNestedMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BankAccountSerializer

    def get_queryset(self):
        investor_id = self.kwargs['investor_id']
        investor = get_object_or_404(InvestorProfile, id=investor_id)
        self.check_investor_permission(investor)
        return BankAccount.objects.filter(investor=investor)

    def perform_create(self, serializer):
        investor = get_object_or_404(InvestorProfile, id=self.kwargs['investor_id'])
        self.check_investor_permission(investor)
        serializer.save(investor=investor)

class BankAccountDetailAPIView(InvestorNestedMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BankAccountSerializer
    queryset = BankAccount.objects.all()

    def get_object(self):
        obj = super().get_object()
        self.check_investor_permission(obj.investor)
        return obj

class NomineeListCreateAPIView(InvestorNestedMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NomineeSerializer

    def get_queryset(self):
        investor_id = self.kwargs['investor_id']
        investor = get_object_or_404(InvestorProfile, id=investor_id)
        self.check_investor_permission(investor)
        return Nominee.objects.filter(investor=investor)

    def perform_create(self, serializer):
        investor = get_object_or_404(InvestorProfile, id=self.kwargs['investor_id'])
        self.check_investor_permission(investor)
        serializer.save(investor=investor)

class NomineeDetailAPIView(InvestorNestedMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NomineeSerializer
    queryset = Nominee.objects.all()

    def get_object(self):
        obj = super().get_object()
        self.check_investor_permission(obj.investor)
        return obj

class DocumentListCreateAPIView(InvestorNestedMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        investor_id = self.kwargs['investor_id']
        investor = get_object_or_404(InvestorProfile, id=investor_id)
        self.check_investor_permission(investor)
        return Document.objects.filter(investor=investor)

    def perform_create(self, serializer):
        investor = get_object_or_404(InvestorProfile, id=self.kwargs['investor_id'])
        self.check_investor_permission(investor)
        serializer.save(investor=investor)

class DocumentDetailAPIView(InvestorNestedMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentSerializer
    queryset = Document.objects.all()

    def get_object(self):
        obj = super().get_object()
        self.check_investor_permission(obj.investor)
        return obj

# --- BSE Actions ---

class PushToBSEAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        investor = get_object_or_404(InvestorProfile, pk=pk)

        # Permission logic (can be extracted to a mixin or helper)
        if request.user.user_type not in [User.Types.RM, User.Types.DISTRIBUTOR, User.Types.ADMIN]:
             return Response({'error': 'Permission denied'}, status=403)

        # 1. Validation
        validation_errors = validate_investor_for_bse(investor)
        if validation_errors:
            return Response({'status': 'error', 'errors': validation_errors}, status=400)

        # 2. Map Data
        try:
            param_string = map_investor_to_bse_param_string(investor)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=400)

        # 3. Call API
        client = BSEStarMFClient()
        regn_type = "MOD" if investor.ucc_code else "NEW"

        try:
            response = client.register_client({'Param': param_string}, regn_type=regn_type)
            if response['status'] == 'success':
                if not investor.ucc_code:
                    investor.ucc_code = investor.pan
                    investor.save()

                remarks = response.get('remarks', '').upper()
                investor.bse_remarks = remarks
                investor.last_verified_at = timezone.now()

                if "AUTHENTICATED" in remarks or "ACTIVE" in remarks:
                    investor.nominee_auth_status = InvestorProfile.AUTH_AUTHENTICATED
                elif "PENDING" in remarks:
                    investor.nominee_auth_status = InvestorProfile.AUTH_PENDING

                investor.save()

                # Trigger FATCA
                client.fatca_upload(investor)

                return Response({'status': 'success', 'message': f"BSE {regn_type} Successful: {remarks}"})
            else:
                remarks = response.get('remarks', '')
                if "FAILED : MODIFICATION NOT FOUND" in remarks.upper():
                     return Response({'status': 'success', 'message': "Already up to date."})
                return Response({'status': 'error', 'message': remarks}, status=400)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=500)

class TriggerAuthAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        investor = get_object_or_404(InvestorProfile, pk=pk)

        if request.user.user_type not in [User.Types.RM, User.Types.DISTRIBUTOR, User.Types.ADMIN]:
             return Response({'error': 'Permission denied'}, status=403)

        if not investor.ucc_code:
            return Response({'status': 'error', 'message': "Investor not registered on BSE"}, status=400)

        # Validation
        validation_errors = validate_investor_for_bse(investor)
        if validation_errors:
             return Response({'status': 'error', 'errors': validation_errors}, status=400)

        try:
            param_string = map_investor_to_bse_param_string(investor)
            client = BSEStarMFClient()
            response = client.register_client({'Param': param_string}, regn_type="MOD")

            investor.bse_remarks = response.get('remarks', '')
            investor.last_verified_at = timezone.now()

            if response['status'] == 'success':
                 remarks = response.get('remarks', '').upper()
                 if "AUTHENTICATED" in remarks or "ACTIVE" in remarks:
                    investor.nominee_auth_status = InvestorProfile.AUTH_AUTHENTICATED
                 elif "PENDING" in remarks:
                    investor.nominee_auth_status = InvestorProfile.AUTH_PENDING

                 investor.save()
                 return Response({'status': 'success', 'message': response.get('remarks')})
            else:
                 return Response({'status': 'error', 'message': response.get('remarks')}, status=400)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=500)

class ToggleKYCAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        investor = get_object_or_404(InvestorProfile, pk=pk)
        if request.user.user_type not in [User.Types.RM, User.Types.DISTRIBUTOR, User.Types.ADMIN]:
             return Response({'error': 'Permission denied'}, status=403)

        investor.kyc_status = not investor.kyc_status
        investor.save()
        return Response({'status': 'success', 'kyc_status': investor.kyc_status})

class FATCAUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        investor = get_object_or_404(InvestorProfile, pk=pk)
        if request.user.user_type not in [User.Types.RM, User.Types.DISTRIBUTOR, User.Types.ADMIN]:
             return Response({'error': 'Permission denied'}, status=403)

        if not investor.ucc_code:
             return Response({'status': 'error', 'message': "Investor not registered on BSE"}, status=400)

        client = BSEStarMFClient()
        try:
            response = client.fatca_upload(investor)
            if response['status'] == 'success':
                return Response({'status': 'success', 'message': response.get('remarks')})
            else:
                return Response({'status': 'error', 'message': response.get('remarks')}, status=400)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=500)

class DistributorMappingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.user_type not in [User.Types.ADMIN, User.Types.RM]:
            return Response({'error': 'Permission denied'}, status=403)

        investor_ids = request.data.get('investor_ids', [])
        distributor_id = request.data.get('distributor_id')

        if not investor_ids:
            return Response({'error': 'No investors selected'}, status=400)

        distributor = None
        if distributor_id:
            try:
                qs = DistributorProfile.objects.all()
                if request.user.user_type == User.Types.RM:
                    qs = qs.filter(rm__user=request.user)
                distributor = qs.get(pk=distributor_id)
            except DistributorProfile.DoesNotExist:
                 return Response({'error': 'Invalid Distributor'}, status=400)

        investors = InvestorProfile.objects.filter(id__in=investor_ids)
        if request.user.user_type == User.Types.RM:
             investors = investors.filter(
                Q(distributor__rm__user=request.user) | Q(rm__user=request.user)
            )

        count = 0
        with transaction.atomic():
            for investor in investors:
                investor.distributor = distributor
                if distributor:
                    investor.rm = distributor.rm
                    if distributor.rm:
                        investor.branch = distributor.rm.branch
                else:
                    if request.user.user_type == User.Types.RM:
                         investor.rm = request.user.rm_profile
                         if investor.rm:
                            investor.branch = investor.rm.branch
                investor.save()
                count += 1

        return Response({'status': 'success', 'count': count})

# --- New API Views for RM & Distributor Management ---

class RMListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__name', 'user__email', 'employee_code']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RMCreateSerializer
        return RMSerializer

    def get_queryset(self):
        user = self.request.user
        if user.user_type == User.Types.ADMIN:
            return RMProfile.objects.all().select_related('user', 'branch').order_by('-id')
        return RMProfile.objects.none()

class RMDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = RMProfile.objects.all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return RMCreateSerializer
        return RMSerializer

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if user.user_type != User.Types.ADMIN:
             self.permission_denied(self.request, message="Only Admins can manage RMs.")
        return obj

class DistributorListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__name', 'user__email', 'arn_number', 'broker_code']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DistributorCreateSerializer
        return DistributorProfileSerializer

    def get_queryset(self):
        user = self.request.user
        if user.user_type == User.Types.ADMIN:
            return DistributorProfile.objects.all().select_related('user', 'rm', 'rm__user').order_by('-id')
        elif user.user_type == User.Types.RM:
            # RMs can see distributors assigned to them
            return DistributorProfile.objects.filter(rm__user=user).select_related('user', 'rm', 'rm__user').order_by('-id')
        return DistributorProfile.objects.none()

    def perform_create(self, serializer):
        # Admin can create anywhere. RM can create but automatically assigned to them?
        # Serializer handles creation. If RM creates, we should enforce assignment.
        if self.request.user.user_type == User.Types.RM:
             serializer.save(rm=self.request.user.rm_profile)
        else:
             serializer.save()

class DistributorDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = DistributorProfile.objects.all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return DistributorCreateSerializer
        return DistributorProfileSerializer

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if user.user_type == User.Types.ADMIN:
            return obj
        elif user.user_type == User.Types.RM:
            if obj.rm and obj.rm.user == user:
                return obj
        self.permission_denied(self.request, message="Permission denied.")

class BranchListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer

class PortfolioAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            investor_profile = user.investor_profile
        except InvestorProfile.DoesNotExist:
             return Response({'error': 'User is not an investor'}, status=400)

        holdings = Holding.objects.filter(investor=investor_profile).select_related('scheme')

        asset_allocation = {}
        sector_allocation = {}
        total_value = 0

        for holding in holdings:
            val = holding.current_value or 0
            total_value += val
            scheme = holding.scheme

            # Asset Allocation
            allocs = scheme.asset_allocations.all()
            if allocs.exists():
                for alloc in allocs:
                    amount = val * (alloc.percentage / 100)
                    asset_allocation[alloc.asset_type] = asset_allocation.get(alloc.asset_type, 0) + amount
            else:
                 # Fallback if no allocation data
                 asset_allocation['Unclassified'] = asset_allocation.get('Unclassified', 0) + val

            # Sector Allocation
            sectors = scheme.sector_allocations.all()
            if sectors.exists():
                for sec in sectors:
                    amount = val * (sec.percentage / 100)
                    sector_allocation[sec.sector_name] = sector_allocation.get(sec.sector_name, 0) + amount
            # else: skip sector logic if data missing

        # Convert to percentages
        asset_data = []
        for k, v in asset_allocation.items():
            if total_value > 0:
                asset_data.append({'name': k, 'value': round(float(v), 2), 'percentage': round(float(v/total_value)*100, 2)})

        sector_data = []
        for k, v in sector_allocation.items():
            if total_value > 0:
                sector_data.append({'name': k, 'value': round(float(v), 2), 'percentage': round(float(v/total_value)*100, 2)})

        return Response({
            'total_value': round(float(total_value), 2),
            'asset_allocation': asset_data,
            'sector_allocation': sector_data
        })

class HoldingListAPIView(InvestorNestedMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        investor_id = request.query_params.get('investor_id')

        investor_profile = None
        if investor_id:
            try:
                investor_profile = InvestorProfile.objects.get(id=investor_id)
                self.check_investor_permission(investor_profile)
            except InvestorProfile.DoesNotExist:
                return Response({'error': 'Investor not found'}, status=404)
        else:
            try:
                investor_profile = user.investor_profile
            except InvestorProfile.DoesNotExist:
                 return Response({'error': 'User is not an investor and no investor_id provided'}, status=400)

        holdings = Holding.objects.filter(investor=investor_profile).select_related('scheme', 'scheme__amc').order_by('-current_value')

        data = []
        for h in holdings:
            data.append({
                'id': h.id,
                'scheme_id': h.scheme.id,
                'scheme_name': h.scheme.name,
                'amc': h.scheme.amc.name if h.scheme.amc else '',
                'folio': h.folio_number,
                'units': h.units,
                'average_cost': h.average_cost,
                'current_value': h.current_value,
                'gain_loss': (h.current_value - (h.units * h.average_cost)) if h.current_value else 0,
                'investor_id': investor_profile.id,
            })

        return Response(data)

class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            'username': user.username,
            'name': user.name,
            'email': user.email,
            'role': user.user_type,
            'mobile_number': getattr(user, 'mobile_number', ''),
        }
        if hasattr(user, 'investor_profile'):
            data['investor_id'] = user.investor_profile.id
        return Response(data)

    def patch(self, request):
        user = request.user
        data = request.data

        if 'name' in data:
            user.name = data['name']
        if 'email' in data:
            user.email = data['email']
        # if 'mobile_number' in data: user.mobile_number = data['mobile_number']

        user.save()
        return Response({'status': 'success', 'message': 'Profile updated successfully'})

class PasswordChangeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not user.check_password(old_password):
            return Response({'status': 'error', 'message': 'Incorrect old password'}, status=400)

        if new_password != confirm_password:
             return Response({'status': 'error', 'message': 'Passwords do not match'}, status=400)

        # Add complexity checks here if needed

        user.set_password(new_password)
        user.save()
        return Response({'status': 'success', 'message': 'Password changed successfully'})


# --- Bulk Upload APIs ---

class RMUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.user_type != User.Types.ADMIN:
            return Response({'error': 'Permission denied'}, status=403)

        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file provided'}, status=400)

        count, errors = import_rms_from_file(file_obj)

        if errors:
            return Response({'status': 'warning', 'message': f'Processed {count} RMs with errors.', 'errors': errors}, status=200)

        return Response({'status': 'success', 'message': f'Successfully imported {count} RMs.'})

class DistributorUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.user_type != User.Types.ADMIN:
            return Response({'error': 'Permission denied'}, status=403)

        file_obj = request.FILES.get('file')
        if not file_obj:
             return Response({'error': 'No file provided'}, status=400)

        count, errors = import_distributors_from_file(file_obj)

        if errors:
             return Response({'status': 'warning', 'message': f'Processed {count} distributors with errors.', 'errors': errors}, status=200)

        return Response({'status': 'success', 'message': f'Successfully imported {count} distributors.'})

class InvestorUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Allow Admin and RM to upload investors? Legacy view said IsAdminMixin.
        # But logically RMs might want to bulk upload their clients.
        # For now, stick to Admin only to match legacy, or open to RM if needed.
        # Let's restrict to Admin for now as per legacy code `InvestorUploadView` which uses `IsAdminMixin`.
        if request.user.user_type != User.Types.ADMIN:
             return Response({'error': 'Permission denied'}, status=403)

        file_obj = request.FILES.get('file')
        if not file_obj:
             return Response({'error': 'No file provided'}, status=400)

        count, errors = import_investors_from_file(file_obj)

        if errors:
             return Response({'status': 'warning', 'message': f'Processed {count} investors with errors.', 'errors': errors}, status=200)

        return Response({'status': 'success', 'message': f'Successfully imported {count} investors.'})

class DownloadRMSampleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.user_type != User.Types.ADMIN:
             return Response({'error': 'Permission denied'}, status=403)

        excel_file = create_excel_sample_file(RM_HEADERS, RM_CHOICES)
        response = HttpResponse(
            excel_file.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="rm_import_sample.xlsx"'
        return response

class DownloadDistributorSampleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.user_type != User.Types.ADMIN:
             return Response({'error': 'Permission denied'}, status=403)

        excel_file = create_excel_sample_file(DISTRIBUTOR_HEADERS, DISTRIBUTOR_CHOICES)
        response = HttpResponse(
            excel_file.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="distributor_import_sample.xlsx"'
        return response

class DownloadInvestorSampleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Allow RM/Admin
        if request.user.user_type not in [User.Types.ADMIN, User.Types.RM]:
             return Response({'error': 'Permission denied'}, status=403)

        excel_file = create_excel_sample_file(INVESTOR_HEADERS, INVESTOR_CHOICES)
        response = HttpResponse(
            excel_file.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="investor_import_sample.xlsx"'
        return response

class RequestPasswordResetAPIView(APIView):
    permission_classes = [] # Public

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal user existence
            return Response({'status': 'success', 'message': 'If an account exists with this email, a reset link has been sent.'})

        if not user.is_active:
             return Response({'error': 'Account is inactive.'}, status=400)

        # Generate Token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Construct Link
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:5173')
        reset_link = f"{frontend_url}/auth/reset-password/{uid}/{token}"

        # Send Email
        logger.info(f"Password Reset Link for {email}: {reset_link}")

        try:
            send_mail(
                subject="Password Reset Request",
                message=f"Click the link to reset your password: {reset_link}",
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@buybestfin.com',
                recipient_list=[email],
                fail_silently=False
            )
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            # Still return success to user

        return Response({'status': 'success', 'message': 'If an account exists with this email, a reset link has been sent.'})

class ResetPasswordConfirmAPIView(APIView):
    permission_classes = []

    def post(self, request):
        uidb64 = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('password')

        if not uidb64 or not token or not new_password:
             return Response({'error': 'Missing required fields'}, status=400)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Invalid link'}, status=400)

        if default_token_generator.check_token(user, token):
            user.set_password(new_password)
            user.save()
            return Response({'status': 'success', 'message': 'Password has been reset successfully.'})
        else:
            return Response({'error': 'Invalid or expired token'}, status=400)
