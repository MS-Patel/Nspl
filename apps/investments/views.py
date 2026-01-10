from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse
from .models import Order, Folio, Mandate
from .forms import OrderForm
from apps.users.models import InvestorProfile, DistributorProfile
from apps.products.models import Scheme, AMC, SchemeCategory
from apps.integration.bse_client import BSEStarMFClient
import logging
import json

logger = logging.getLogger(__name__)

@login_required
def order_create(request):
    """
    Purchase Order Creation View.
    Handles order creation for various user roles.
    """
    user = request.user
    initial_data = {}

    # Pre-fill data if available in GET params (e.g., from Scheme Explorer)
    if 'scheme' in request.GET:
        scheme_id = request.GET.get('scheme')
        try:
            scheme = Scheme.objects.get(id=scheme_id)
            initial_data['scheme'] = scheme
        except Scheme.DoesNotExist:
            pass

    if request.method == 'POST':
        form = OrderForm(request.POST, user=user)
        if form.is_valid():
            order = form.save(commit=False)

            # Additional Logic: Check if new folio is requested
            if form.cleaned_data.get('folio_selection'):
                 # Use existing folio
                 order.folio = form.cleaned_data['folio_selection']
                 order.is_new_folio = False
            else:
                 # Request new folio
                 order.is_new_folio = True

            # Handle SIP logic
            if order.transaction_type == Order.SIP:
                # Ensure mandate is selected
                if not order.mandate:
                     # This should ideally be caught by form validation
                     messages.error(request, "Mandate is required for SIP orders.")
                     # Re-render with context
                     return render_order_form(request, form)

            # Set Distributor/Investor relationships based on logged-in user
            # (Already partly handled in form validation, but safe to enforce here)
            if user.user_type == 'INVESTOR':
                order.investor = user.investor_profile
                order.distributor = user.investor_profile.distributor

            order.save()

            # Execute Order on BSE (Lumpsum only for now)
            if order.transaction_type in [Order.PURCHASE, Order.REDEMPTION, Order.SWITCH]:
                try:
                    client = BSEStarMFClient()
                    result = client.place_order(order)

                    if result['status'] == 'success':
                        order.status = Order.SENT_TO_BSE
                        order.bse_order_id = result.get('bse_order_id')
                        order.bse_remarks = result.get('remarks')
                        messages.success(request, f"Order {order.unique_ref_no} placed on BSE: {result.get('remarks')}")
                    else:
                        order.status = Order.REJECTED
                        order.bse_remarks = result.get('remarks')
                        messages.error(request, f"BSE Error: {result.get('remarks')}")

                    order.save()

                except Exception as e:
                    logger.exception("Error placing order on BSE")
                    order.status = Order.REJECTED
                    order.bse_remarks = f"System Error: {str(e)}"
                    order.save()
                    messages.error(request, f"Order saved but failed to push to BSE: {str(e)}")
            else:
                messages.success(request, f"Order {order.unique_ref_no} created locally (SIP execution pending).")

            return redirect('order_list') # Redirect to order list
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = OrderForm(initial=initial_data, user=user)

    return render_order_form(request, form)

def render_order_form(request, form):
    """Helper to render the form with necessary context data."""
    context = {
        'form': form,
        'title': 'New Purchase',
        'amcs': AMC.objects.all(),
        'categories': SchemeCategory.objects.all(),
    }
    return render(request, 'investments/order_form.html', context)

@login_required
def order_list(request):
    user = request.user
    if user.user_type == 'ADMIN':
        orders = Order.objects.all()
    elif user.user_type == 'RM':
        # RM sees orders from their distributors' investors
        orders = Order.objects.filter(distributor__rm__user=user)
    elif user.user_type == 'DISTRIBUTOR':
        orders = Order.objects.filter(distributor__user=user)
    elif user.user_type == 'INVESTOR':
        orders = Order.objects.filter(investor__user=user)
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
            'amount': float(order.amount),
            'status': order.get_status_display(),
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
    scheme_type = request.GET.get('scheme_type') # 'growth', 'idcw', etc. if available

    schemes_qs = Scheme.objects.filter(purchase_allowed=True)
    if amc_id:
        schemes_qs = schemes_qs.filter(amc_id=amc_id)
    if category_id:
        schemes_qs = schemes_qs.filter(category_id=category_id)

    # Optimizing query: return only needed fields
    schemes_data = schemes_qs.values(
        'id', 'name', 'scheme_code', 'min_purchase_amount', 'max_purchase_amount',
        'purchase_amount_multiplier', 'is_sip_allowed'
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
                'is_sip_allowed': scheme.is_sip_allowed
            }
        except Scheme.DoesNotExist:
            pass

    return JsonResponse(response_data)

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
