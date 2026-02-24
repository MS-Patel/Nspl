from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from .models import RMProfile, DistributorProfile, InvestorProfile
from apps.reconciliation.models import Holding
from apps.investments.models import Order, SIP
from .serializers import OrderSerializer
from apps.reconciliation.utils.valuation import calculate_portfolio_valuation
from apps.integration.sync_utils import sync_pending_orders, sync_sip_child_orders
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

        # Placeholder for RM specific stats if any
        return Response({'message': 'RM Dashboard API'})

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
