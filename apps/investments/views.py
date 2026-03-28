from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Order, Folio, Mandate, SIP, SIPInstallment
from .forms import OrderForm, MandateForm, RedemptionForm
from apps.users.models import InvestorProfile, DistributorProfile
from apps.products.models import Scheme, AMC, SchemeCategory, NAVHistory
from apps.reconciliation.models import Holding, Transaction
from apps.investments.templatetags.investment_extras import readable_txn_type
from .utils import calculate_xirr, get_cash_flows
from django.utils import timezone
from datetime import datetime, timedelta, date
from apps.integration.bse_client import BSEStarMFClient
from apps.integration.sync_utils import sync_pending_orders
import logging
import json
import math

logger = logging.getLogger(__name__)

def has_access_to_investor(user, investor_id):
    """Helper to check if a user has access to a specific investor."""
    try:
        investor = InvestorProfile.objects.get(id=investor_id)
    except InvestorProfile.DoesNotExist:
        return False

    if user.user_type == 'ADMIN':
        return True
    if user.user_type == 'INVESTOR':
        return user.investor_profile.id == int(investor_id)
    if user.user_type == 'DISTRIBUTOR':
        return investor.distributor.user == user
    if user.user_type == 'RM':
        return investor.distributor.rm.user == user

    return False

@method_decorator(login_required, name='dispatch')
class RedemptionCreateView(CreateView):
    template_name = 'investments/redemption_form.html'
    form_class = RedemptionForm

    def get_holding(self):
        holding_id = self.kwargs.get('holding_id')
        return get_object_or_404(Holding, id=holding_id)

    def dispatch(self, request, *args, **kwargs):
        holding = self.get_holding()
        # Verify access
        if not has_access_to_investor(request.user, holding.investor.id):
             return HttpResponseForbidden("You do not have access to this investment.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['holding'] = self.get_holding()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['holding'] = self.get_holding()
        context['title'] = "Redeem Funds"
        return context

    def form_valid(self, form):
        holding = self.get_holding()
        data = form.cleaned_data

        # Create Order
        order = Order(
            investor=holding.investor,
            scheme=holding.scheme,
            folio=Folio.objects.filter(folio_number=holding.folio_number, investor=holding.investor).first(), # Try to link actual Folio object
            transaction_type=Order.REDEMPTION,
            status=Order.PENDING,
            all_redeem=data.get('all_redeem', False)
        )

        # Handle Distributor mapping (Copied from Order Create logic)
        # If user is Distributor, link them. If Investor, link their distributor.
        user = self.request.user
        if user.user_type == 'DISTRIBUTOR':
            order.distributor = user.distributor_profile
        elif user.user_type == 'RM':
             # RM placing order for investor -> Investor's distributor
             order.distributor = holding.investor.distributor
        elif user.user_type == 'INVESTOR':
            order.distributor = holding.investor.distributor
        elif user.user_type == 'ADMIN':
             order.distributor = holding.investor.distributor

        # Set Amount/Units based on Type
        if data['redemption_type'] == 'AMOUNT':
            order.amount = data['value']
            order.units = 0
        elif data['redemption_type'] == 'UNITS':
            order.amount = 0
            order.units = data['value']
        elif data['redemption_type'] == 'ALL':
            order.amount = 0
            order.units = 0 # BSE ignores Qty/Val if AllRedeem is Y
            order.all_redeem = True

        order.save()

        # Push to BSE
        should_redirect = True
        try:
            client = BSEStarMFClient()
            result = client.place_order(order)

            if result['status'] == 'success':
                order.status = Order.SENT_TO_BSE
                order.bse_order_id = result.get('bse_order_id')
                order.bse_remarks = result.get('remarks')
                messages.success(self.request, f"Redemption Order Placed. Ref: {result.get('remarks')}")
            elif result['status'] == 'exception':
                order.status = Order.PENDING
                order.bse_remarks = f"System Error: {result.get('remarks')}"
                messages.error(self.request, f"System Error (Order saved as Pending): {result.get('remarks')}")
            else:
                order.status = Order.REJECTED
                order.bse_remarks = result.get('remarks')
                messages.error(self.request, f"BSE Error: {result.get('remarks')}")
                should_redirect = False  # Stay on page to allow resubmission

            order.save()

        except Exception as e:
            logger.exception("Error placing redemption order on BSE")
            order.status = Order.PENDING
            order.bse_remarks = f"System Error: {str(e)}"
            order.save()
            messages.error(self.request, f"System Error (Order saved as Pending): {str(e)}")

        if should_redirect:
            return redirect('investments:order_list')

        return self.render_to_response(self.get_context_data(form=form))


@method_decorator(login_required, name='dispatch')
class MandateCreateView(CreateView):
    model = Mandate
    form_class = MandateForm
    template_name = 'investments/mandate_form.html'

    def get_initial(self):
        initial = super().get_initial()
        investor_id = self.request.GET.get('investor_id')
        if investor_id:
            try:
                investor = InvestorProfile.objects.get(id=investor_id)
                if has_access_to_investor(self.request.user, investor_id):
                    initial['investor'] = investor
            except InvestorProfile.DoesNotExist:
                pass
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        mandate = form.save(commit=False)
        # Verify access
        if not has_access_to_investor(self.request.user, mandate.investor.id):
             return HttpResponseForbidden("You do not have access to this investor.")

        # Default Mandate ID (Will be updated by BSE)
        import uuid
        mandate.mandate_id = f"TEMP-{uuid.uuid4().hex[:8].upper()}"
        mandate.save()

        # Push to BSE
        try:
            client = BSEStarMFClient()
            result = client.register_mandate(mandate)

            if result['status'] == 'success':
                mandate.mandate_id = result['mandate_id']
                mandate.status = Mandate.PENDING # Set to PENDING initially for E-Mandate
                mandate.save()

                messages.success(self.request, f"Mandate Registered. Please authorize it via the link below.")

                # Check if we should redirect to auth or list
                # For now, redirect to investor detail where they can click "Authorize"
            elif result['status'] == 'exception':
                mandate.status = Mandate.PENDING
                mandate.save()
                messages.error(self.request, f"System Error (Mandate saved): {result['remarks']}")
            else:
                mandate.status = Mandate.REJECTED
                mandate.save()
                messages.error(self.request, f"BSE Mandate Error: {result['remarks']}")

        except Exception as e:
            logger.exception("Mandate Registration Failed")
            mandate.status = Mandate.PENDING
            mandate.save()
            messages.error(self.request, f"System Error (Mandate saved as Pending): {str(e)}")

        # self.object might not be set if we are not calling super().form_valid(form)
        self.object = mandate
        return redirect(self.get_success_url())

    def get_success_url(self):
        investor = self.object.investor
        return reverse('users:investor_detail', kwargs={'pk': investor.pk})

class MandateRetryView(LoginRequiredMixin, View):
    def post(self, request, pk):
        mandate = get_object_or_404(Mandate, pk=pk)

        # Access Check
        if not has_access_to_investor(request.user, mandate.investor.id):
             return HttpResponseForbidden("You do not have access to this mandate.")

        # State Check
        if mandate.is_bse_submitted or mandate.status != Mandate.PENDING:
             messages.warning(request, "This mandate cannot be retried.")
             return redirect('users:investor_detail', pk=mandate.investor.pk)

        # Retry Submission
        try:
            client = BSEStarMFClient()
            result = client.register_mandate(mandate)

            if result['status'] == 'success':
                mandate.mandate_id = result['mandate_id']
                mandate.status = Mandate.PENDING
                mandate.save()
                messages.success(request, "Mandate submitted successfully. Please authorize it.")
            elif result['status'] == 'exception':
                # Still failed (network/system), but we keep it pending for another retry
                messages.error(request, f"System Error (Retry failed): {result['remarks']}")
            else:
                # BSE Rejected it
                mandate.status = Mandate.REJECTED
                mandate.save()
                messages.error(request, f"BSE Rejected Mandate: {result['remarks']}")

        except Exception as e:
            logger.exception("Mandate Retry Failed")
            mandate.status = Mandate.PENDING
            mandate.save()
            messages.error(request, f"System Error (Mandate remains Pending): {str(e)}")

        return redirect('users:investor_detail', pk=mandate.investor.pk)

@login_required
def mandate_authorize(request, pk):
    """
    Redirects the user to the BSE E-Mandate Authorization Page.
    """
    mandate = get_object_or_404(Mandate, pk=pk)

    # IDOR Check
    if not has_access_to_investor(request.user, mandate.investor.id):
        return HttpResponseForbidden("You do not have access to this mandate.")

    # Only allow authorization for Pending mandates (or Approved if re-auth needed? usually Pending)
    # Actually, if it's already approved, no need. But in UAT/Demo, we might want to test flow.
    # Allowing it for now.

    client_code = mandate.investor.ucc_code if mandate.investor.ucc_code else mandate.investor.pan

    try:
        client = BSEStarMFClient()
        # Generate absolute loopback URL for BSE to redirect back to
        loopback_url = request.build_absolute_uri(
            reverse('users:investor_detail', kwargs={'pk': mandate.investor.pk})
        )
        auth_url = client.get_mandate_auth_url(client_code, mandate.mandate_id, loopback_url)
        return redirect(auth_url)
    except Exception as e:
        logger.error(f"Error generating auth URL: {e}")
        messages.error(request, "Could not generate authorization URL.")
        return redirect('users:investor_detail', pk=mandate.investor.pk)

@login_required
def order_create(request):
    """
    Purchase Order Creation View.
    Handles order creation for various user roles.
    """
    user = request.user
    initial_data = {}

    # Transaction Type Mapping (URL Param -> Model Choice)
    txn_type_map = {
        'PURCHASE': Order.PURCHASE,
        'SWITCH': Order.SWITCH,
        'SIP': Order.SIP,
        'REDEMPTION': Order.REDEMPTION
    }

    # Pre-fill data if available in GET params (e.g., from Scheme Explorer or Holding)
    if 'holding_id' in request.GET:
        holding_id = request.GET.get('holding_id')
        try:
            holding = Holding.objects.get(id=holding_id)
            # Verify Access
            if has_access_to_investor(user, holding.investor.id):
                initial_data['investor'] = holding.investor
                initial_data['scheme'] = holding.scheme

                # Determine Transaction Type
                txn_param = request.GET.get('transaction_type')
                if txn_param:
                    initial_data['transaction_type'] = txn_type_map.get(txn_param, txn_param)
                else:
                    initial_data['transaction_type'] = Order.SWITCH

                # Attempt to link Folio
                folio = Folio.objects.filter(investor=holding.investor, folio_number=holding.folio_number).first()
                if folio:
                    initial_data['folio_selection'] = folio
        except Holding.DoesNotExist:
            pass

    # Allow scheme or scheme_id param
    scheme_param = request.GET.get('scheme') or request.GET.get('scheme_id')
    if scheme_param and 'scheme' not in initial_data:
        try:
            scheme = Scheme.objects.get(id=scheme_param)
            initial_data['scheme'] = scheme

            # Determine Transaction Type if passed
            txn_param = request.GET.get('transaction_type')
            if txn_param:
                initial_data['transaction_type'] = txn_type_map.get(txn_param, txn_param)

            # Attempt to find existing folio for this investor and AMC
            # Determine investor context
            investor = None
            if user.user_type == 'INVESTOR':
                investor = user.investor_profile
            elif initial_data.get('investor'):
                investor = initial_data.get('investor')

            if investor:
                 # Check for folio with same AMC
                 # We pick the latest updated one if multiple exist
                 existing_folio = Folio.objects.filter(investor=investor, amc=scheme.amc).order_by('-updated_at').first()
                 if existing_folio:
                     initial_data['folio_selection'] = existing_folio

        except Scheme.DoesNotExist:
            pass

    if request.method == 'POST':
        form = OrderForm(request.POST, user=user)
        if form.is_valid():
            order = form.save(commit=False)
            should_redirect = True

            # Additional Logic: Check if new folio is requested
            if form.cleaned_data.get('folio_selection'):
                 # Use existing folio
                 order.folio = form.cleaned_data['folio_selection']
                 order.is_new_folio = False
            else:
                 # Request new folio
                 order.is_new_folio = True

            # Set Distributor/Investor relationships based on logged-in user
            if user.user_type == 'INVESTOR':
                order.investor = user.investor_profile
                order.distributor = user.investor_profile.distributor

            # Handle SIP Registration
            if order.transaction_type == Order.SIP:
                # 1. Create SIP Object
                try:
                    sip = SIP.objects.create(
                        investor=order.investor,
                        scheme=order.scheme,
                        folio=order.folio,
                        mandate=order.mandate,
                        amount=order.amount,
                        frequency=form.cleaned_data['sip_frequency'],
                        start_date=form.cleaned_data['sip_start_date'],
                        installments=form.cleaned_data['sip_installments']
                    )

                    # 2. Link SIP to Order
                    order.sip_reg = sip
                    order.save() # Save order to generate ID

                    # 3. Call BSE XSIP API
                    client = BSEStarMFClient()
                    result = client.register_sip(sip)

                    if result['status'] == 'success':
                        sip.bse_sip_id = result['bse_sip_id']
                        sip.bse_reg_no = result['bse_reg_no']
                        sip.status = SIP.STATUS_ACTIVE
                        sip.save()

                        # Generate expected installments for this new SIP
                        from .services import generate_sip_installments
                        generate_sip_installments(sip)

                        order.status = Order.SENT_TO_BSE
                        order.bse_order_id = result['bse_reg_no'] # Use Reg No as Order ID ref
                        order.bse_remarks = result['remarks']
                        order.save()

                        messages.success(request, f"SIP Registered Successfully! Reg No: {result['bse_reg_no']}")
                    elif result['status'] == 'exception':
                        # Keep SIP as Pending
                        sip.status = SIP.STATUS_PENDING
                        sip.save()
                        order.status = Order.PENDING
                        order.bse_remarks = f"System Error: {result['remarks']}"
                        order.save()
                        messages.error(request, f"System Error (SIP saved as Pending): {result['remarks']}")
                    else:
                        sip.status = SIP.STATUS_PENDING # Or Rejected
                        sip.save()
                        order.status = Order.REJECTED
                        order.bse_remarks = result['remarks']
                        order.save()
                        messages.error(request, f"BSE SIP Error: {result['remarks']}")
                        should_redirect = False

                except Exception as e:
                    logger.exception("SIP Registration Failed")
                    order.status = Order.PENDING
                    order.bse_remarks = f"System Error: {str(e)}"
                    order.save()
                    messages.error(request, f"System Error (SIP saved as Pending): {str(e)}")

            # Execute Lumpsum Order on BSE
            elif order.transaction_type in [Order.PURCHASE, Order.REDEMPTION]:
                order.save()
                try:
                    client = BSEStarMFClient()
                    result = client.place_order(order)

                    if result['status'] == 'success':
                        order.status = Order.SENT_TO_BSE
                        order.bse_order_id = result.get('bse_order_id')
                        order.bse_remarks = result.get('remarks')
                        messages.success(request, f"Order {order.unique_ref_no} placed on BSE: {result.get('remarks')}")
                    elif result['status'] == 'exception':
                        order.status = Order.PENDING
                        order.bse_remarks = f"System Error: {result.get('remarks')}"
                        order.save()
                        messages.error(request, f"System Error (Order saved as Pending): {result.get('remarks')}")
                    else:
                        order.status = Order.REJECTED
                        order.bse_remarks = result.get('remarks')
                        messages.error(request, f"BSE Error: {result.get('remarks')}")
                        should_redirect = False

                    order.save()

                except Exception as e:
                    logger.exception("Error placing order on BSE")
                    order.status = Order.PENDING
                    order.bse_remarks = f"System Error: {str(e)}"
                    order.save()
                    messages.error(request, f"System Error (Order saved as Pending): {str(e)}")

            # Execute Switch Order on BSE
            elif order.transaction_type == Order.SWITCH:
                order.save()
                try:
                    client = BSEStarMFClient()
                    # Determine switch type from form data if needed, or rely on order fields
                    # The Order model fields (units, amount, all_redeem) are already set by form.save()
                    result = client.switch_order(order)

                    if result['status'] == 'success':
                        order.status = Order.SENT_TO_BSE
                        order.bse_order_id = result.get('bse_order_id')
                        order.bse_remarks = result.get('remarks')
                        messages.success(request, f"Switch Order {order.unique_ref_no} placed on BSE: {result.get('remarks')}")
                    elif result['status'] == 'exception':
                        order.status = Order.PENDING
                        order.bse_remarks = f"System Error: {result.get('remarks')}"
                        order.save()
                        messages.error(request, f"System Error (Order saved as Pending): {result.get('remarks')}")
                    else:
                        order.status = Order.REJECTED
                        order.bse_remarks = result.get('remarks')
                        messages.error(request, f"BSE Error: {result.get('remarks')}")
                        should_redirect = False

                    order.save()

                except Exception as e:
                    logger.exception("Error placing switch order on BSE")
                    order.status = Order.PENDING
                    order.bse_remarks = f"System Error: {str(e)}"
                    order.save()
                    messages.error(request, f"System Error (Order saved as Pending): {str(e)}")

            if should_redirect:
                return redirect('investments:order_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Default to PURCHASE if not specified
        if 'transaction_type' not in initial_data:
            initial_data['transaction_type'] = Order.PURCHASE
        form = OrderForm(initial=initial_data, user=user)

    return render_order_form(request, form)

def render_order_form(request, form):
    """Helper to render the form with necessary context data."""
    # Get distinct scheme types for the filter
    scheme_types = Scheme.objects.values_list('scheme_type', flat=True).distinct().order_by('scheme_type')
    scheme_plans = Scheme.objects.values_list('scheme_plan', flat=True).distinct().order_by('scheme_plan')

    context = {
        'form': form,
        'title': 'New Purchase / SIP',
        'amcs': AMC.objects.filter(is_active=True),
        'categories': SchemeCategory.objects.all(),
        'scheme_types': [st for st in scheme_types if st], # Filter out None/Empty
        'scheme_plans': [sp for sp in scheme_plans if sp], # Filter out None/Empty
    }
    return render(request, 'investments/order_form.html', context)

@login_required
def order_list(request):
    user = request.user

    # Sync pending orders for this user context before loading
    try:
        sync_pending_orders(user)
    except Exception as e:
        logger.error(f"Failed to sync pending orders: {e}")

    # Optimize query with select_related to avoid N+1 queries
    queryset = Order.objects.select_related('investor__user', 'scheme')

    if user.user_type == 'ADMIN':
        orders = queryset.all()
    elif user.user_type == 'RM':
        # RM sees orders from their distributors' investors
        orders = queryset.filter(distributor__rm__user=user)
    elif user.user_type == 'DISTRIBUTOR':
        orders = queryset.filter(distributor__user=user)
    elif user.user_type == 'INVESTOR':
        orders = queryset.filter(investor__user=user)
    else:
        orders = Order.objects.none()

    data = []
    for order in orders:
        data.append({
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
            'unique_ref_no': order.unique_ref_no,
            'investor_name': order.investor.user.name if order.investor.user.name else order.investor.user.username,
            'scheme_name': order.scheme.name,
            'transaction_type': order.get_transaction_type_display(),
            'amount': round(float(order.amount), 2),
            'status': order.get_status_display(),
            'bse_remarks': order.bse_remarks if order.bse_remarks else '-',
            'bse_order_id': order.bse_order_id if order.bse_order_id else '-',
        })

    return render(request, 'investments/order_list.html', {'grid_data_json': json.dumps(data)})

@login_required
def get_investor_folios(request):
    """
    API endpoint to fetch folios for a specific investor and scheme.
    Used for dynamic dropdowns.
    IDOR Protection: Checks if the logged-in user has access to the investor.
    """
    investor_id = request.GET.get('investor_id')
    scheme_id = request.GET.get('scheme_id')

    if not investor_id:
        return JsonResponse({'folios': []})

    # IDOR Check
    if not has_access_to_investor(request.user, investor_id):
         return JsonResponse({'error': 'Unauthorized access to investor data'}, status=403)

    folios_qs = Folio.objects.filter(investor_id=investor_id)

    # Filter by AMC if scheme is selected
    if scheme_id:
        try:
            scheme = Scheme.objects.get(id=scheme_id)
            folios_qs = folios_qs.filter(amc=scheme.amc)
        except Scheme.DoesNotExist:
            pass

    data = [{'id': f.id, 'display': str(f)} for f in folios_qs]
    return JsonResponse({'folios': data})

@login_required
def get_order_metadata(request):
    """
    API endpoint to fetch metadata for cascading dropdowns.
    Returns:
    - investors: based on distributor_id (or current user context)
    - schemes: based on filters (amc, category, type)
    - mandates: based on investor_id
    - scheme_details: if scheme_id is provided
    """
    response_data = {}

    # 1. Fetch Investors (Filtered by Distributor)
    # Only Admin/RM should typically need this if they select Distributor first.
    # For now, we rely on the Distributor ID passed.
    distributor_id = request.GET.get('distributor_id')
    if distributor_id:
        # Permission Check: Can this user view this distributor's investors?
        if request.user.user_type == 'ADMIN' or \
           (request.user.user_type == 'RM' and request.user.rm_profile.distributors.filter(id=distributor_id).exists()) or \
           (request.user.user_type == 'DISTRIBUTOR' and request.user.distributor_profile.id == int(distributor_id)):

            investors = InvestorProfile.objects.filter(distributor_id=distributor_id).values('id', 'user__username', 'pan')
            response_data['investors'] = list(investors)

    # 2. Fetch Schemes (Filtered) - Public Read (Authenticated)
    amc_id = request.GET.get('amc_id')
    category_id = request.GET.get('category_id')
    scheme_type = request.GET.get('scheme_type')
    scheme_plan = request.GET.get('scheme_plan')
    transaction_type = request.GET.get('transaction_type')

    schemes_qs = Scheme.objects.filter(amc_active_flag=True)

    # Filter based on transaction type if provided
    if transaction_type == 'P':
        schemes_qs = schemes_qs.filter(purchase_allowed=True)
    elif transaction_type == 'R':
        schemes_qs = schemes_qs.filter(redemption_allowed=True)
    elif transaction_type == 'SIP':
        schemes_qs = schemes_qs.filter(is_sip_allowed=True)
    elif transaction_type == 'S':
        schemes_qs = schemes_qs.filter(is_switch_allowed=True)
    else:
        # Fallback to general purchase-allowed schemes if no type specified
        schemes_qs = schemes_qs.filter(purchase_allowed=True)

    if amc_id:
        schemes_qs = schemes_qs.filter(amc_id=amc_id)
    if category_id:
        schemes_qs = schemes_qs.filter(category_id=category_id)
    if scheme_type:
        schemes_qs = schemes_qs.filter(scheme_type=scheme_type)
    if scheme_plan:
        schemes_qs = schemes_qs.filter(scheme_plan=scheme_plan)

    # Optimizing query: return only needed fields
    schemes_data = schemes_qs.values(
        'id', 'name', 'scheme_code', 'isin', 'min_purchase_amount', 'max_purchase_amount',
        'purchase_amount_multiplier', 'is_sip_allowed', 'is_switch_allowed', 'amc_id'
    )

    if request.GET.get('fetch_schemes') == 'true':
         response_data['schemes'] = list(schemes_data)

    # 3. Fetch Mandates
    investor_id = request.GET.get('investor_id')
    if investor_id:
        # IDOR Check
        if has_access_to_investor(request.user, investor_id):
            mandates = Mandate.objects.filter(
                investor_id=investor_id,
                status=Mandate.APPROVED
            ).values('id', 'mandate_id', 'amount_limit', 'bank_account__bank_name', 'bank_account__account_number')
            response_data['mandates'] = list(mandates)

    # 4. Fetch Scheme Details (Specific Scheme) - Public Read (Authenticated)
    scheme_id = request.GET.get('scheme_id')
    if scheme_id:
        try:
            scheme = Scheme.objects.get(id=scheme_id)
            response_data['scheme_details'] = {
                'id': scheme.id,
                'name': scheme.name,
                'min_purchase_amount': scheme.min_purchase_amount,
                'max_purchase_amount': scheme.max_purchase_amount,
                'purchase_amount_multiplier': scheme.purchase_amount_multiplier,
                'is_sip_allowed': scheme.is_sip_allowed,
                'amc_id': scheme.amc.id
            }
        except Scheme.DoesNotExist:
            pass

    return JsonResponse(response_data)

class HoldingListView(LoginRequiredMixin, ListView):
    model = Holding
    template_name = 'investments/holding_list.html'
    context_object_name = 'holdings'

    def get_queryset(self):
        user = self.request.user
        User = get_user_model()
        qs = super().get_queryset().select_related('investor', 'scheme', 'investor__user')

        if user.user_type == User.Types.ADMIN:
            return qs
        elif user.user_type == User.Types.RM:
             # Holdings of investors where (distributor.rm == self) OR (rm == self)
             return qs.filter(Q(investor__distributor__rm__user=user) | Q(investor__rm__user=user))
        elif user.user_type == User.Types.DISTRIBUTOR:
            return qs.filter(investor__distributor__user=user)
        elif user.user_type == User.Types.INVESTOR:
            return qs.filter(investor__user=user)
        return qs.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = []
        for holding in self.get_queryset():
            data.append({
                'investor_name': holding.investor.user.name or holding.investor.user.username,
                'folio_number': holding.folio_number,
                'scheme_name': holding.scheme.name,
                'units': round(float(holding.units), 2),
                'average_cost': round(float(holding.average_cost), 2),
                'current_value': round(float(holding.current_value) if holding.current_value else 0.0, 2),
                'current_nav': round(float(holding.current_nav) if holding.current_nav else 0.0, 2),
                'folio_url': reverse('investments:folio_detail', kwargs={'folio_number': holding.folio_number}),
                'action_url': {
                    'redeem': reverse('investments:redemption_create', args=[holding.id]),
                    'switch': reverse('investments:order_create') + f"?holding_id={holding.id}&transaction_type=SWITCH"
                }
            })
        context['grid_data_json'] = json.dumps(data)
        return context

class FolioDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'investments/folio_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        folio_number = self.kwargs.get('folio_number')
        user = self.request.user
        User = get_user_model()

        # 1. Fetch Holdings (Scope Check)
        qs = Holding.objects.filter(folio_number=folio_number).select_related('investor', 'scheme', 'investor__user', 'scheme__amc')

        if user.user_type == User.Types.ADMIN:
            pass # No filter
        elif user.user_type == User.Types.RM:
             qs = qs.filter(Q(investor__distributor__rm__user=user) | Q(investor__rm__user=user))
        elif user.user_type == User.Types.DISTRIBUTOR:
            qs = qs.filter(investor__distributor__user=user)
        elif user.user_type == User.Types.INVESTOR:
            qs = qs.filter(investor__user=user)
        else:
            qs = qs.none()

        holdings = list(qs)
        if not holdings:
             raise Http404("Folio not found or access denied.")

        # 2. Folio Summary
        first_holding = holdings[0]
        investor = first_holding.investor
        amc = first_holding.scheme.amc

        total_current_value = 0.0
        total_invested_value = 0.0

        # Portfolio XIRR Preparation
        all_cash_flows = []

        # Allocation Data
        allocation_labels = []
        allocation_series = []

        fund_data = []

        today = timezone.now().date()
        one_year_ago = today - timedelta(days=365)

        for h in holdings:
            cv = float(h.current_value) if h.current_value else 0.0
            u = float(h.units)
            ac = float(h.average_cost)
            iv = u * ac

            total_current_value += cv
            total_invested_value += iv

            # Prepare Allocation Data
            if cv > 0:
                allocation_labels.append(h.scheme.name)
                allocation_series.append(round(cv, 2))

            # 3. Calculate XIRR
            scheme_flows = get_cash_flows(h)
            all_cash_flows.extend(scheme_flows)

            xirr_val = calculate_xirr(scheme_flows)
            xirr_percent = round(xirr_val * 100, 2) if xirr_val is not None else None

            # 4. Fetch NAV History & Calculate Day's Change
            # Fetch last 2 NAVs for change, and last 365 days for Sparkline
            navs = NAVHistory.objects.filter(
                scheme=h.scheme,
                nav_date__gte=one_year_ago
            ).order_by('-nav_date')

            # Convert to list for slicing/processing to avoid multiple queries
            nav_list = list(navs) # This fetches all (up to 365)

            days_change = 0.0
            days_change_percent = 0.0
            nav_date = None

            if len(nav_list) >= 1:
                latest = nav_list[0]
                nav_date = latest.nav_date

                if len(nav_list) >= 2:
                    prev = nav_list[1]
                    change = float(latest.net_asset_value - prev.net_asset_value)
                    days_change = change * u
                    if prev.net_asset_value > 0:
                        days_change_percent = (change / float(prev.net_asset_value)) * 100
                else:
                    # Only 1 NAV available (New Scheme?)
                    pass

            # Sparkline Data (Chronological)
            sparkline_data = []
            for n in reversed(nav_list): # Reverse to get oldest first
                # ApexCharts expects timestamp in ms
                ts = int(datetime.combine(n.nav_date, datetime.min.time()).timestamp() * 1000)
                sparkline_data.append([ts, float(n.net_asset_value)])

            # 5. Transactions for this Scheme & Folio
            txns = Transaction.objects.filter(
                folio_number=folio_number,
                scheme=h.scheme,
                investor=investor
            ).order_by('-date', '-created_at')

            transactions_data = []
            for txn in txns:
                sip_amt = float(txn.amount) + float(txn.stamp_duty or 0)
                amount = float(txn.amount)
                units = float(txn.units)
                nav = float(txn.nav) if txn.nav else None

                if math.isnan(sip_amt): sip_amt = 0.0
                if math.isnan(amount): amount = 0.0
                if math.isnan(units): units = 0.0
                if nav is not None and math.isnan(nav): nav = 0.0

                transactions_data.append({
                    'date': txn.date.strftime('%Y-%m-%d'),
                    'type': txn.txn_type or readable_txn_type(txn.txn_type_code),
                    'sip_amount': sip_amt,
                    'amount': amount,
                    'units': units,
                    'nav': nav,
                })

            fund_data.append({
                'scheme': h.scheme,
                'holding': h,
                'current_value': cv,
                'invested_value': iv,
                'gain_loss': cv - iv,
                'xirr': xirr_percent,
                'days_change': days_change,
                'days_change_percent': days_change_percent,
                'nav_date': nav_date,
                'sparkline_data': json.dumps(sparkline_data),
                'transactions': txns,
                'transactions_json': json.dumps(transactions_data),
                'total_txns_count': txns.count()
            })

        # Calculate Portfolio XIRR
        portfolio_xirr_val = calculate_xirr(all_cash_flows)
        portfolio_xirr_percent = round(portfolio_xirr_val * 100, 2) if portfolio_xirr_val is not None else None

        context['folio_number'] = folio_number
        context['investor'] = investor
        context['amc'] = amc
        context['summary'] = {
            'total_current_value': total_current_value,
            'total_invested_value': total_invested_value,
            'total_gain_loss': total_current_value - total_invested_value,
            'portfolio_xirr': portfolio_xirr_percent,
        }
        context['allocation'] = {
            'labels': json.dumps(allocation_labels),
            'series': json.dumps(allocation_series)
        }
        context['fund_data'] = fund_data

        return context

class PortfolioInvestorListView(LoginRequiredMixin, ListView):
    model = InvestorProfile
    template_name = 'investments/portfolio_investor_list.html'
    context_object_name = 'investors'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.user_type == 'INVESTOR':
            try:
                profile = request.user.investor_profile
                return redirect('investments:investor_portfolio', investor_id=profile.id)
            except InvestorProfile.DoesNotExist:
                pass
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        qs = InvestorProfile.objects.select_related('user', 'distributor', 'distributor__user')

        # Filter by Role
        if user.user_type == 'ADMIN':
            pass
        elif user.user_type == 'RM':
             qs = qs.filter(Q(distributor__rm__user=user) | Q(rm__user=user))
        elif user.user_type == 'DISTRIBUTOR':
            qs = qs.filter(distributor__user=user)
        elif user.user_type == 'INVESTOR':
            qs = qs.filter(user=user)
        else:
            qs = qs.none()

        # Annotate with Total AUM
        qs = qs.annotate(total_aum=Sum('holdings__current_value'))

        # Return investors even if AUM is 0, but sort by AUM desc
        return qs.order_by('-total_aum', 'user__name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = []
        for inv in self.get_queryset():
            aum = inv.total_aum or 0

            # Action URL to the new portfolio dashboard
            # Assuming URL name 'investor_portfolio'
            try:
                action_url = reverse('investments:investor_portfolio', args=[inv.id])
            except:
                action_url = "#" # Fallback until URL is configured

            data.append({
                'id': inv.id,
                'name': inv.user.name or inv.user.username,
                'pan': inv.pan,
                'distributor': inv.distributor.user.name if inv.distributor and inv.distributor.user.name else (inv.distributor.user.username if inv.distributor else '-'),
                'total_aum': round(float(aum), 2),
                'action_url': action_url
            })
        context['grid_data_json'] = json.dumps(data)
        return context

class InvestorPortfolioView(LoginRequiredMixin, TemplateView):
    template_name = 'investments/investor_portfolio_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        investor_id = self.kwargs.get('investor_id')
        user = self.request.user

        # 1. Fetch Investor & Check Access
        try:
            investor = InvestorProfile.objects.get(id=investor_id)
        except InvestorProfile.DoesNotExist:
             raise Http404("Investor not found")

        if not has_access_to_investor(user, investor_id):
             raise Http404("Access Denied")

        # 2. Fetch Holdings
        holdings = Holding.objects.filter(investor=investor).select_related('scheme', 'scheme__amc')

        # 3. Aggregate
        total_current_value = 0.0
        total_invested_value = 0.0

        # Group by Folio Number
        folios_map = {}

        # Get all transactions to compute Purchase, Redemption, Switch IN/OUT for each folio
        transactions = Transaction.objects.filter(investor=investor)

        # Aggregate transactions by folio
        from django.db.models import Sum

        for h in holdings:
            cv = float(h.current_value) if h.current_value else 0.0
            iv = float(h.units * h.average_cost)

            total_current_value += cv
            total_invested_value += iv

            f_num = h.folio_number
            if f_num not in folios_map:
                amc_name = h.scheme.amc.name if h.scheme and h.scheme.amc else "Unknown AMC"

                folios_map[f_num] = {
                    'folio_number': f_num,
                    'amc_name': amc_name,
                    'current_value': 0.0,
                    'invested_value': 0.0,
                    'gain_loss': 0.0,
                    'gain_loss_percent': 0.0,
                    'folio_url': reverse('investments:folio_detail', kwargs={'folio_number': f_num})
                }

            folios_map[f_num]['current_value'] += cv
            folios_map[f_num]['invested_value'] += iv


        # Calculate Gain/Loss per Folio
        folio_list = []
        for f_num, data in folios_map.items():
            current = data['current_value']
            invested = data['invested_value']
            gain_loss = current - invested
            percent = (gain_loss / invested * 100) if invested > 0 else 0.0

            data['gain_loss'] = round(gain_loss, 2)
            data['gain_loss_percent'] = round(percent, 2)
            data['current_value'] = round(current, 2)
            data['invested_value'] = round(invested, 2)

            folio_list.append(data)

        # 4. Context
        context['investor'] = investor
        context['summary'] = {
            'total_current_value': round(total_current_value, 2),
            'total_invested_value': round(total_invested_value, 2),
            'total_gain_loss': round(total_current_value - total_invested_value, 2),
        }

        # Calculate Portfolio Percent
        if total_invested_value > 0:
            context['summary']['gain_loss_percent'] = round(((total_current_value - total_invested_value) / total_invested_value) * 100, 2)
        else:
            context['summary']['gain_loss_percent'] = 0.0

        context['folio_list_json'] = json.dumps(folio_list)

        return context

from django.http import HttpResponse
from apps.reports.services.pdf_generator import (
    generate_wealth_report_pdf,
    generate_pl_report_pdf,
    generate_capital_gain_pdf,
    generate_transaction_statement_pdf
)

class ExportWealthReportView(LoginRequiredMixin, View):
    def get(self, request, investor_id):
        # Fetch data similar to InvestorPortfolioView
        try:
            investor = InvestorProfile.objects.get(id=investor_id)
        except InvestorProfile.DoesNotExist:
            raise Http404("Investor not found")

        if not has_access_to_investor(request.user, investor_id):
            raise Http404("Access Denied")

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        holdings = Holding.objects.filter(investor=investor).select_related('scheme', 'scheme__amc')
        total_current_value = 0.0
        total_invested_value = 0.0
        folios_map = {}
        all_cash_flows = []

        # Get all transactions to compute Purchase, Redemption, Switch IN/OUT for each folio
        transactions = Transaction.objects.filter(investor=investor)
        from django.db.models import Sum

        for h in holdings:
            cv = float(h.current_value) if h.current_value else 0.0
            iv = float(h.units * h.average_cost)
            total_current_value += cv
            total_invested_value += iv

            scheme_flows = get_cash_flows(h)
            all_cash_flows.extend(scheme_flows)

            f_num = h.folio_number
            if f_num not in folios_map:
                amc_name = h.scheme.amc.name if h.scheme and h.scheme.amc else "Unknown AMC"

                # Fetch aggregated transactions for this holding
                folio_txns = transactions.filter(folio_number=f_num, scheme=h.scheme)
                purchase = float(folio_txns.filter(txn_type__in=['Purchase', 'SIP', 'Dividend Reinvestment']).aggregate(Sum('amount'))['amount__sum'] or 0.0)
                switch_in = float(folio_txns.filter(txn_type__in=['Switch In']).aggregate(Sum('amount'))['amount__sum'] or 0.0)
                redemption = float(folio_txns.filter(txn_type__in=['Redemption', 'SWP']).aggregate(Sum('amount'))['amount__sum'] or 0.0)
                switch_out = float(folio_txns.filter(txn_type__in=['Switch Out']).aggregate(Sum('amount'))['amount__sum'] or 0.0)

                folios_map[f_num] = {
                    'folio_number': f_num,
                    'amc_name': amc_name,
                    'current_value': 0.0,
                    'invested_value': 0.0,
                    'gain_loss': 0.0,
                    'gain_loss_percent': 0.0,
                    'purchase': purchase,
                    'switch_in': switch_in,
                    'redemption': redemption,
                    'switch_out': switch_out,
                }
            else:
                folio_txns = transactions.filter(folio_number=f_num, scheme=h.scheme)
                folios_map[f_num]['purchase'] += float(folio_txns.filter(txn_type__in=['Purchase', 'SIP', 'Dividend Reinvestment']).aggregate(Sum('amount'))['amount__sum'] or 0.0)
                folios_map[f_num]['switch_in'] += float(folio_txns.filter(txn_type__in=['Switch In']).aggregate(Sum('amount'))['amount__sum'] or 0.0)
                folios_map[f_num]['redemption'] += float(folio_txns.filter(txn_type__in=['Redemption', 'SWP']).aggregate(Sum('amount'))['amount__sum'] or 0.0)
                folios_map[f_num]['switch_out'] += float(folio_txns.filter(txn_type__in=['Switch Out']).aggregate(Sum('amount'))['amount__sum'] or 0.0)

            folios_map[f_num]['current_value'] += cv
            folios_map[f_num]['invested_value'] += iv

        folio_list = []
        for f_num, data in folios_map.items():
            current = data['current_value']
            invested = data['invested_value']
            gain_loss = current - invested
            percent = (gain_loss / invested * 100) if invested > 0 else 0.0
            data['gain_loss'] = round(gain_loss, 2)
            data['gain_loss_percent'] = round(percent, 2)
            data['current_value'] = round(current, 2)
            data['invested_value'] = round(invested, 2)
            folio_list.append(data)

        portfolio_xirr_val = calculate_xirr(all_cash_flows)
        portfolio_xirr_percent = round(portfolio_xirr_val * 100, 2) if portfolio_xirr_val is not None else None

        summary = {
            'total_current_value': round(total_current_value, 2),
            'total_invested_value': round(total_invested_value, 2),
            'total_gain_loss': round(total_current_value - total_invested_value, 2),
            'portfolio_xirr': portfolio_xirr_percent,
        }
        if total_invested_value > 0:
            summary['gain_loss_percent'] = round(((total_current_value - total_invested_value) / total_invested_value) * 100, 2)
        else:
            summary['gain_loss_percent'] = 0.0

        buffer = generate_wealth_report_pdf(investor, summary, folio_list, start_date=start_date, end_date=end_date)

        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Wealth_Report_{investor.pan}.pdf"'
        return response


class ExportPLReportView(LoginRequiredMixin, View):
    def get(self, request, investor_id):
        try:
            investor = InvestorProfile.objects.get(id=investor_id)
        except InvestorProfile.DoesNotExist:
            raise Http404("Investor not found")

        if not has_access_to_investor(request.user, investor_id):
            raise Http404("Access Denied")

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        holdings = Holding.objects.filter(investor=investor).select_related('scheme', 'scheme__amc')
        total_current_value = 0.0
        total_invested_value = 0.0
        folios_map = {}
        all_cash_flows = []

        for h in holdings:
            cv = float(h.current_value) if h.current_value else 0.0
            iv = float(h.units * h.average_cost)
            total_current_value += cv
            total_invested_value += iv
            scheme_flows = get_cash_flows(h)
            all_cash_flows.extend(scheme_flows)

            f_num = h.folio_number
            if f_num not in folios_map:
                amc_name = h.scheme.amc.name if h.scheme and h.scheme.amc else "Unknown AMC"
                folios_map[f_num] = {
                    'folio_number': f_num,
                    'amc_name': amc_name,
                    'current_value': 0.0,
                    'invested_value': 0.0,
                    'gain_loss': 0.0,
                    'gain_loss_percent': 0.0,
                }
            folios_map[f_num]['current_value'] += cv
            folios_map[f_num]['invested_value'] += iv

        folio_list = []
        for f_num, data in folios_map.items():
            current = data['current_value']
            invested = data['invested_value']
            gain_loss = current - invested
            percent = (gain_loss / invested * 100) if invested > 0 else 0.0
            data['gain_loss'] = round(gain_loss, 2)
            data['gain_loss_percent'] = round(percent, 2)
            data['current_value'] = round(current, 2)
            data['invested_value'] = round(invested, 2)
            folio_list.append(data)

        portfolio_xirr_val = calculate_xirr(all_cash_flows)
        portfolio_xirr_percent = round(portfolio_xirr_val * 100, 2) if portfolio_xirr_val is not None else None

        summary = {
            'total_current_value': round(total_current_value, 2),
            'total_invested_value': round(total_invested_value, 2),
            'total_gain_loss': round(total_current_value - total_invested_value, 2),
            'portfolio_xirr': portfolio_xirr_percent,
        }

        buffer = generate_pl_report_pdf(investor, summary, folio_list, start_date=start_date, end_date=end_date)

        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="PL_Report_{investor.pan}.pdf"'
        return response


class ExportCapitalGainReportView(LoginRequiredMixin, View):
    def get(self, request, investor_id):
        try:
            investor = InvestorProfile.objects.get(id=investor_id)
        except InvestorProfile.DoesNotExist:
            raise Http404("Investor not found")

        if not has_access_to_investor(request.user, investor_id):
            raise Http404("Access Denied")

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        transactions = Transaction.objects.filter(investor=investor).order_by('-date', '-units')

        if start_date:
            transactions = transactions.filter(date__gte=start_date)
        if end_date:
            transactions = transactions.filter(date__lte=end_date)

        buffer = generate_capital_gain_pdf(investor, transactions, fy_start=start_date, fy_end=end_date)

        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Capital_Gain_Report_{investor.pan}.pdf"'
        return response


class ExportTransactionStatementView(LoginRequiredMixin, View):
    def get(self, request, investor_id):
        try:
            investor = InvestorProfile.objects.get(id=investor_id)
        except InvestorProfile.DoesNotExist:
            raise Http404("Investor not found")

        if not has_access_to_investor(request.user, investor_id):
            raise Http404("Access Denied")

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        transactions = Transaction.objects.filter(investor=investor,date__gte=start_date,date__lte=end_date).order_by('date', '-units')

        # Note: Do not filter transactions here if generate_transaction_statement_pdf handles opening balance via `date__lt`
        # But if generate_transaction_statement_pdf takes transactions as input and filters within, let's look at it.
        # However, looking at standard implementation, generate_transaction_statement_pdf accepts the full list or a filtered list.
        # Based on instructions, we will pass dates to the generator.

        buffer = generate_transaction_statement_pdf(investor, transactions, fy_start=start_date, fy_end=end_date)

        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Transaction_Statement_{investor.pan}.pdf"'
        return response


class SIPInsightsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, sip_id):
        try:
            sip = SIP.objects.get(id=sip_id, investor__user=request.user)
        except SIP.DoesNotExist:
            return Response({"error": "SIP not found."}, status=404)

        installments = sip.sip_installments.all()

        total_installments = installments.count()
        completed = installments.filter(status=SIPInstallment.STATUS_SUCCESS).count()
        pending = installments.filter(status__in=[SIPInstallment.STATUS_PENDING, SIPInstallment.STATUS_TRIGGERED]).count()
        failed = installments.filter(status=SIPInstallment.STATUS_FAILED).count()
        skipped = installments.filter(status=SIPInstallment.STATUS_SKIPPED).count()

        # Success rate calculation
        attempted = completed + failed
        success_rate = round((completed / attempted) * 100, 2) if attempted > 0 else 0.0

        next_installment = installments.filter(
            status__in=[SIPInstallment.STATUS_PENDING, SIPInstallment.STATUS_TRIGGERED],
            due_date__gte=date.today()
        ).order_by('due_date').first()

        next_inst_data = None
        if next_installment:
            next_inst_data = {
                "date": next_installment.due_date,
                "amount": next_installment.expected_amount,
                "status": next_installment.status
            }

        timeline = [
            {
                "id": inst.id,
                "date": inst.due_date,
                "amount": inst.expected_amount,
                "status": inst.status,
                "failure_reason": inst.failure_reason,
                "transaction_id": inst.transaction.id if inst.transaction else None,
                "order_id": inst.order_id
            }
            for inst in installments.order_by('-due_date')
        ]

        data = {
            "summary": {
                "total_installments": total_installments,
                "completed": completed,
                "pending": pending,
                "failed": failed,
                "skipped": skipped
            },
            "next_installment": next_inst_data,
            "health": {
                "success_rate": success_rate,
                "failure_count": failed
            },
            "timeline": timeline
        }
        return Response(data)

class SIPDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'investments/sip_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Determine the base queryset for SIPs
        sips = SIP.objects.select_related('investor', 'investor__user', 'scheme')

        if user.user_type == 'ADMIN':
            pass
        elif user.user_type == 'RM':
            sips = sips.filter(Q(investor__distributor__rm__user=user) | Q(investor__rm__user=user))
        elif user.user_type == 'DISTRIBUTOR':
            sips = sips.filter(investor__distributor__user=user)
        elif user.user_type == 'INVESTOR':
            sips = sips.filter(investor__user=user)
        else:
            sips = sips.none()

        # Calculate Aggregate Metrics
        active_sips = sips.filter(status=SIP.STATUS_ACTIVE)
        total_active_sips = active_sips.count()

        # Only sum the amount for active SIPs
        total_monthly_amount = active_sips.aggregate(total=Sum('amount'))['total'] or 0

        # Calculate Success Rate
        # Installments belong to the filtered SIPs
        installments = SIPInstallment.objects.filter(sip_master__in=sips)
        completed_inst = installments.filter(status=SIPInstallment.STATUS_SUCCESS).count()
        failed_inst = installments.filter(status=SIPInstallment.STATUS_FAILED).count()
        attempted_inst = completed_inst + failed_inst
        success_rate = round((completed_inst / attempted_inst) * 100, 2) if attempted_inst > 0 else 0.0

        total_investors = sips.values('investor').distinct().count()

        # Build list for data table
        # We need Investor Name, Scheme, Amount, Status, and Next Installment Date
        sip_list = []
        for sip in sips.order_by('-created_at'):
            sip_list.append({
                'id': sip.id,
                'investor_name': f"{sip.investor.user.first_name} {sip.investor.user.last_name}".strip() or sip.investor.user.username,
                'scheme_name': sip.scheme.name,
                'amount': sip.amount,
                'status': sip.get_status_display(),
                'status_class': sip.status,
                'next_installment_date': sip.next_installment_date,
            })

        context.update({
            'total_active_sips': total_active_sips,
            'total_monthly_amount': total_monthly_amount,
            'success_rate': success_rate,
            'total_investors': total_investors,
            'sips': sip_list,
            'user_type': user.user_type,
        })

        return context


class UpcomingSIPInstallmentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        from .services import get_upcoming_installments

        installments = get_upcoming_installments(days).filter(sip_master__investor__user=request.user)

        data = [
            {
                "sip_id": inst.sip_master.id,
                "scheme_name": inst.sip_master.scheme.name,
                "due_date": inst.due_date,
                "amount": inst.expected_amount,
                "status": inst.status
            }
            for inst in installments.order_by('due_date')
        ]

        return Response(data)
