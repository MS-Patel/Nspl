from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Q
from .models import RMProfile, DistributorProfile, InvestorProfile
from apps.reconciliation.models import Holding
from apps.investments.models import Order, SIP
from .serializers import OrderSerializer, InvestorSerializer
from apps.reconciliation.utils.valuation import calculate_portfolio_valuation
from apps.integration.sync_utils import sync_pending_orders, sync_sip_child_orders, sync_pending_mandates
from django.contrib.auth import get_user_model
import logging
import json

User = get_user_model()
logger = logging.getLogger(__name__)

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
        holdings_json = []

        if investor_profile:
            valuation_data = calculate_portfolio_valuation(investor_profile)
            # holdings = valuation_data.get('holdings', [])
            # holdings_json = json.dumps(holdings, default=str) # Frontend expects JSON array
            # Actually, let's return the object directly

        return Response({
            'valuation': valuation_data
        })

class UserMeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'username': user.username,
            'name': user.name,
            'email': user.email,
            'role': user.user_type,
            'id': user.id
        })

# --- Investor Module API Views ---

class InvestorListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InvestorSerializer

    def get_queryset(self):
        user = self.request.user
        qs = InvestorProfile.objects.select_related(
            'user', 'distributor', 'distributor__user', 'rm', 'rm__user'
        ).prefetch_related(
            'bank_accounts', 'nominees', 'documents'
        )

        if user.user_type == User.Types.DISTRIBUTOR:
            return qs.filter(distributor__user=user)
        elif user.user_type == User.Types.RM:
            # RM sees investors where (distributor.rm == self) OR (rm == self [Direct])
            return qs.filter(Q(distributor__rm__user=user) | Q(rm__user=user))
        elif user.user_type == User.Types.ADMIN:
            return qs

        return qs.none()

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
