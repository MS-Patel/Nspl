from rest_framework import generics, status, views, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Order, SIP, Mandate, Folio
from apps.products.models import Scheme
from apps.users.models import InvestorProfile, BankAccount
from apps.integration.bse_client import BSEStarMFClient
from .serializers import (
    OrderCreateSerializer, OrderListSerializer,
    SIPListSerializer, MandateSerializer, MandateCreateSerializer
)
import logging
import uuid

logger = logging.getLogger(__name__)

class OrderListAPIView(generics.ListAPIView):
    """
    API View to list orders with filtering.
    """
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.select_related('investor', 'scheme').order_by('-created_at')

        # Role-based filtering
        if user.user_type == 'ADMIN':
            pass
        elif user.user_type == 'RM':
            queryset = queryset.filter(distributor__rm__user=user)
        elif user.user_type == 'DISTRIBUTOR':
            queryset = queryset.filter(distributor__user=user)
        elif user.user_type == 'INVESTOR':
            queryset = queryset.filter(investor__user=user)
        else:
            return Order.objects.none()

        # Additional Filtering
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        investor_id = self.request.query_params.get('investor_id')
        if investor_id:
            queryset = queryset.filter(investor_id=investor_id)

        return queryset

class OrderCreateAPIView(generics.CreateAPIView):
    """
    API View to create orders (Purchase, SIP, Switch, Redeem).
    """
    serializer_class = OrderCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user

        # Determine Investor
        investor_id = request.data.get('investor_id')
        if not investor_id:
            if user.user_type == 'INVESTOR':
                investor = user.investor_profile
            else:
                return Response({"detail": "Investor ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            investor = get_object_or_404(InvestorProfile, id=investor_id)

        scheme = get_object_or_404(Scheme, id=request.data.get('scheme_id'))

        # Prepare Order Object
        order = Order(
            investor=investor,
            scheme=scheme,
            transaction_type=data.get('transaction_type', Order.PURCHASE),
            amount=data.get('amount', 0),
            units=data.get('units', 0),
            payment_mode=data.get('payment_mode', Order.DIRECT),
            all_redeem=data.get('all_redeem', False),
            status=Order.PENDING
        )

        # Link Distributor
        if user.user_type == 'DISTRIBUTOR':
            order.distributor = user.distributor_profile
        elif user.user_type == 'RM':
             order.distributor = investor.distributor
        elif user.user_type == 'INVESTOR':
            order.distributor = investor.distributor
        elif user.user_type == 'ADMIN':
             order.distributor = investor.distributor

        # Link Folio
        folio_number = data.get('folio_number')
        if folio_number:
            folio = Folio.objects.filter(investor=investor, folio_number=folio_number).first()
            if folio:
                order.folio = folio
        else:
             order.is_new_folio = True

        # Link Target Scheme (Switch)
        if data.get('transaction_type') == Order.SWITCH:
            target_scheme_id = data.get('target_scheme_id')
            if target_scheme_id:
                order.target_scheme = get_object_or_404(Scheme, id=target_scheme_id)

        # Handle SIP Specifics
        if data.get('transaction_type') == Order.SIP:
            mandate_id = data.get('mandate_id')
            mandate = get_object_or_404(Mandate, id=mandate_id)
            order.mandate = mandate

            # Create SIP Record first
            sip = SIP.objects.create(
                investor=investor,
                scheme=scheme,
                folio=order.folio,
                mandate=mandate,
                amount=order.amount,
                frequency=data.get('sip_frequency'),
                start_date=data.get('sip_start_date'),
                installments=data.get('sip_installments'),
                status=SIP.STATUS_PENDING
            )
            order.sip_reg = sip
            order.save()

            # Call BSE
            try:
                client = BSEStarMFClient()
                result = client.register_sip(sip)

                if result['status'] == 'success':
                    sip.bse_sip_id = result.get('bse_sip_id')
                    sip.bse_reg_no = result.get('bse_reg_no')
                    sip.status = SIP.STATUS_ACTIVE
                    sip.save()

                    order.status = Order.SENT_TO_BSE
                    order.bse_order_id = result.get('bse_reg_no')
                    order.bse_remarks = result.get('remarks')
                    order.save()
                    return Response({'status': 'success', 'message': 'SIP Registered Successfully', 'bse_reg_no': result.get('bse_reg_no')}, status=status.HTTP_201_CREATED)
                else:
                    sip.status = SIP.STATUS_PENDING
                    sip.save()
                    order.status = Order.REJECTED
                    order.bse_remarks = result.get('remarks')
                    order.save()
                    return Response({'status': 'error', 'message': result.get('remarks')}, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                logger.exception("SIP Registration Failed")
                order.bse_remarks = str(e)
                order.save()
                return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Handle Lumpsum / Switch / Redeem
        else:
            order.save()
            try:
                client = BSEStarMFClient()
                if order.transaction_type == Order.SWITCH:
                    result = client.switch_order(order)
                else:
                    result = client.place_order(order)

                if result['status'] == 'success':
                    order.status = Order.SENT_TO_BSE
                    order.bse_order_id = result.get('bse_order_id')
                    order.bse_remarks = result.get('remarks')
                    order.save()
                    return Response({'status': 'success', 'message': 'Order Placed Successfully', 'bse_order_id': result.get('bse_order_id')}, status=status.HTTP_201_CREATED)
                else:
                    order.status = Order.REJECTED
                    order.bse_remarks = result.get('remarks')
                    order.save()
                    return Response({'status': 'error', 'message': result.get('remarks')}, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                logger.exception("Order Placement Failed")
                order.bse_remarks = str(e)
                order.save()
                return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SIPListAPIView(generics.ListAPIView):
    serializer_class = SIPListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = SIP.objects.select_related('investor', 'scheme').order_by('-created_at')

        if user.user_type == 'ADMIN':
            pass
        elif user.user_type == 'RM':
            queryset = queryset.filter(investor__distributor__rm__user=user)
        elif user.user_type == 'DISTRIBUTOR':
            queryset = queryset.filter(investor__distributor__user=user)
        elif user.user_type == 'INVESTOR':
            queryset = queryset.filter(investor__user=user)
        else:
            return SIP.objects.none()

        return queryset

class SIPCancelAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        sip = get_object_or_404(SIP, pk=pk)

        # Access Check (Simplified for now)
        if request.user.user_type == 'INVESTOR' and sip.investor.user != request.user:
             return Response({"detail": "Access Denied"}, status=status.HTTP_403_FORBIDDEN)

        # TODO: Call BSE API to cancel
        sip.status = SIP.STATUS_CANCELLED
        sip.save()

        return Response({'status': 'success', 'message': 'SIP Cancelled Successfully'})

class MandateListAPIView(generics.ListAPIView):
    serializer_class = MandateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Mandate.objects.select_related('investor', 'bank_account').order_by('-created_at')

        if user.user_type == 'ADMIN':
            pass
        elif user.user_type == 'RM':
            queryset = queryset.filter(investor__distributor__rm__user=user)
        elif user.user_type == 'DISTRIBUTOR':
            queryset = queryset.filter(investor__distributor__user=user)
        elif user.user_type == 'INVESTOR':
            queryset = queryset.filter(investor__user=user)
        else:
            return Mandate.objects.none()

        return queryset

class MandateCreateAPIView(generics.CreateAPIView):
    serializer_class = MandateCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user
        investor_id = data.get('investor_id')
        bank_account_id = data.get('bank_account_id')

        investor = get_object_or_404(InvestorProfile, id=investor_id)
        bank_account = get_object_or_404(BankAccount, id=bank_account_id)

        # Create Mandate Object
        mandate = Mandate(
            investor=investor,
            bank_account=bank_account,
            amount_limit=data.get('amount_limit'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            mandate_type=data.get('mandate_type', Mandate.ISIP),
            mandate_id=f"TEMP-{uuid.uuid4().hex[:8].upper()}",
            status=Mandate.PENDING
        )
        mandate.save()

        # Call BSE to register
        try:
            client = BSEStarMFClient()
            result = client.register_mandate(mandate)

            if result['status'] == 'success':
                mandate.mandate_id = result.get('mandate_id', mandate.mandate_id)
                mandate.save()

                # Generate Auth URL
                loopback_url = request.build_absolute_uri('/') + "dashboard/mandates" # Simplified
                try:
                    auth_url = client.get_mandate_auth_url(investor.ucc_code or investor.pan, mandate.mandate_id, loopback_url)
                    return Response({
                        'status': 'success',
                        'message': 'Mandate Registered. Please authorize.',
                        'mandate_id': mandate.mandate_id,
                        'auth_url': auth_url
                    }, status=status.HTTP_201_CREATED)
                except Exception as e:
                    return Response({
                        'status': 'success',
                        'message': 'Mandate Registered but failed to get Auth URL.',
                        'mandate_id': mandate.mandate_id
                    }, status=status.HTTP_201_CREATED)

            else:
                mandate.status = Mandate.REJECTED
                mandate.save()
                return Response({'status': 'error', 'message': result.get('remarks')}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("Mandate Registration Failed")
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
