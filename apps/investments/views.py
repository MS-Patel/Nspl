from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.http import Http404

from .models import Order, Folio, Mandate, SIP
from .forms import OrderForm, MandateForm, RedemptionForm
from apps.users.models import InvestorProfile, DistributorProfile
from apps.products.models import Scheme, AMC, SchemeCategory, NAVHistory
from apps.reconciliation.models import Holding, Transaction
from apps.investments.templatetags.investment_extras import readable_txn_type
from .utils import calculate_xirr, get_cash_flows
from django.utils import timezone
from datetime import datetime, timedelta
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

# RedemptionCreateView Removed (Legacy)
# MandateCreateView Removed (Legacy)

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

# order_create, render_order_form, order_list Removed (Legacy)

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
    distributor_id = request.GET.get('distributor_id')

    # Auto-detect distributor for Distributor users
    if not distributor_id and request.user.user_type == 'DISTRIBUTOR':
        distributor_id = request.user.distributor_profile.id

    if distributor_id:
        # Permission Check: Can this user view this distributor's investors?
        if request.user.user_type == 'ADMIN' or \
           (request.user.user_type == 'RM' and request.user.rm_profile.distributors.filter(id=distributor_id).exists()) or \
           (request.user.user_type == 'DISTRIBUTOR' and request.user.distributor_profile.id == int(distributor_id)):

            investors = InvestorProfile.objects.filter(distributor_id=distributor_id).values('id', 'user__username', 'pan')
            response_data['investors'] = list(investors)

    # Handle RM case (Fetch all investors linked to RM if no distributor selected)
    elif request.user.user_type == 'RM':
        investors = InvestorProfile.objects.filter(
            Q(distributor__rm__user=request.user) | Q(rm__user=request.user)
        ).values('id', 'user__username', 'pan')
        response_data['investors'] = list(investors)

    # 2. Fetch Schemes (Filtered) - Public Read (Authenticated)
    amc_id = request.GET.get('amc_id')
    category_id = request.GET.get('category_id')
    scheme_type = request.GET.get('scheme_type')
    scheme_plan = request.GET.get('scheme_plan')

    schemes_qs = Scheme.objects.filter(purchase_allowed=True, amc_active_flag=True)
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
        'id', 'name', 'scheme_code', 'min_purchase_amount', 'max_purchase_amount',
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
                    'type': readable_txn_type(txn.txn_type_code),
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
