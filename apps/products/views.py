from django.views.generic import TemplateView, DetailView, FormView, ListView, UpdateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Scheme, AMC, SchemeCategory
from .forms import (
    SchemeUploadForm, NAVUploadForm, SchemeForm,
    SchemeHoldingFormSet, SchemeSectorFormSet,
    SchemeAssetFormSet, SchemeManagerFormSet
)
from apps.users.models import User # Explicit import of custom User model
import pandas as pd
from django.utils import timezone
from .utils.parsers import import_schemes_from_file, import_navs_from_file
from apps.core.utils.excel_generator import create_excel_sample_file
from apps.core.utils.sample_headers import (
    SCHEME_HEADERS, SCHEME_CHOICES,
    NAV_HEADERS, NAV_CHOICES
)
from .utils.calculations import get_scheme_returns, get_peer_comparison
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q

User = get_user_model()

class SchemeListView(LoginRequiredMixin, TemplateView):
    template_name = 'products/scheme_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Prepare data for Grid.js
        schemes = Scheme.objects.select_related('amc', 'category').all()

        # Format: [id, name, scheme_code, isin, category, type, min_purchase]
        # Adjust columns based on requirements
        data = []
        for s in schemes:
            data.append({
                'id': s.id,
                'name': s.name,
                'scheme_code': s.scheme_code,
                'rta_code': s.rta_scheme_code,
                'isin': s.isin,
                'category': s.category.name if s.category else '',
                'scheme_type': s.scheme_type or '',
                'nav': 'N/A', # Placeholder for now, or fetch from NAVHistory
                'min_purchase': round(float(s.min_purchase_amount), 2),
            })

        context['grid_data_json'] = json.dumps(data, cls=DjangoJSONEncoder)
        return context

class SchemeExplorerView(LoginRequiredMixin, ListView):
    model = Scheme
    template_name = 'products/scheme_explore.html'
    context_object_name = 'schemes'
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset().select_related('amc', 'category')

        # Filtering
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(scheme_code__icontains=search_query) |
                Q(isin__icontains=search_query)
            )

        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        amc_id = self.request.GET.get('amc')
        if amc_id:
            queryset = queryset.filter(amc_id=amc_id)

        risk = self.request.GET.get('risk')
        if risk:
            queryset = queryset.filter(riskometer=risk)

        scheme_type = self.request.GET.get('scheme_type')
        if scheme_type:
             queryset = queryset.filter(scheme_type=scheme_type)

        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calculate returns for displayed schemes
        for scheme in context['schemes']:
             scheme.calculated_returns = get_scheme_returns(scheme)
             # Fetch latest NAV explicitly if needed, but we can access via nav_history reversed
             latest_nav = scheme.nav_history.order_by('-nav_date').first()
             scheme.latest_nav_val = latest_nav.net_asset_value if latest_nav else None
             scheme.latest_nav_date = latest_nav.nav_date if latest_nav else None

        # Filter Options
        context['categories'] = SchemeCategory.objects.all().order_by('name')
        context['amcs'] = AMC.objects.filter(is_active=True).order_by('name')
        context['risks'] = [c[0] for c in Scheme.RISKOMETER_CHOICES]
        # Get distinct scheme types from DB to avoid empty options, exclude None/Empty
        context['scheme_types'] = [t for t in Scheme.objects.values_list('scheme_type', flat=True).distinct().order_by('scheme_type') if t]

        # Preserve query params for pagination
        query_params = self.request.GET.copy()
        if 'page' in query_params:
            del query_params['page']
        context['query_params'] = query_params.urlencode()

        return context

class SchemeDetailView(LoginRequiredMixin, DetailView):
    model = Scheme
    template_name = 'products/scheme_detail.html'
    context_object_name = 'scheme'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        scheme = self.object

        # Fetch NAV History for Graph
        # optimize: limit to last 1 year or so if data is huge, but for now take all
        nav_history = scheme.nav_history.order_by('nav_date').values('nav_date', 'net_asset_value')

        chart_data = []
        for item in nav_history:
            chart_data.append({
                'x': item['nav_date'].strftime('%Y-%m-%d'),
                'y': float(item['net_asset_value'])
            })

        context['nav_history_json'] = json.dumps(chart_data)

        # Get latest NAV for display
        latest_nav = scheme.nav_history.order_by('-nav_date').first()
        context['latest_nav'] = latest_nav.net_asset_value if latest_nav else "N/A"
        context['latest_nav_date'] = latest_nav.nav_date if latest_nav else ""

        # New: Fetch Allocations
        context['asset_allocation'] = list(scheme.asset_allocations.values('asset_type', 'percentage'))
        context['sector_allocation'] = list(scheme.sector_allocations.values('sector_name', 'percentage'))

        # New: Fetch Managers
        context['managers'] = scheme.managers.select_related('manager').all()

        # New: Fetch Holdings
        context['top_holdings'] = scheme.scheme_holdings.order_by('-percentage')[:10]

        # New: Returns
        returns = get_scheme_returns(scheme)
        context['returns_1y'] = returns['1Y']
        context['returns_3y'] = returns['3Y']
        context['returns_5y'] = returns['5Y']

        # New: Peer Comparison
        context['peer_comparison'] = get_peer_comparison(scheme)

        # JSON for Allocation Charts
        context['asset_allocation_json'] = json.dumps(context['asset_allocation'], cls=DjangoJSONEncoder)
        context['sector_allocation_json'] = json.dumps(context['sector_allocation'], cls=DjangoJSONEncoder)

        return context

class SchemeUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Scheme
    form_class = SchemeForm
    template_name = 'products/scheme_form.html'

    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN

    def get_success_url(self):
        return reverse_lazy('products:scheme_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['holding_formset'] = SchemeHoldingFormSet(self.request.POST, instance=self.object)
            context['sector_formset'] = SchemeSectorFormSet(self.request.POST, instance=self.object)
            context['asset_formset'] = SchemeAssetFormSet(self.request.POST, instance=self.object)
            context['manager_formset'] = SchemeManagerFormSet(self.request.POST, instance=self.object)
        else:
            context['holding_formset'] = SchemeHoldingFormSet(instance=self.object)
            context['sector_formset'] = SchemeSectorFormSet(instance=self.object)
            context['asset_formset'] = SchemeAssetFormSet(instance=self.object)
            context['manager_formset'] = SchemeManagerFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        holding_formset = context['holding_formset']
        sector_formset = context['sector_formset']
        asset_formset = context['asset_formset']
        manager_formset = context['manager_formset']

        if (holding_formset.is_valid() and sector_formset.is_valid() and
            asset_formset.is_valid() and manager_formset.is_valid()):
            self.object = form.save()
            holding_formset.instance = self.object
            holding_formset.save()
            sector_formset.instance = self.object
            sector_formset.save()
            asset_formset.instance = self.object
            asset_formset.save()
            manager_formset.instance = self.object
            manager_formset.save()
            messages.success(self.request, "Scheme updated successfully.")
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class SchemeUploadView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'products/upload_scheme.html'
    form_class = SchemeUploadForm
    success_url = reverse_lazy('products:scheme_list')

    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN

    def form_valid(self, form):
        file_obj = self.request.FILES['file']
        count, errors = import_schemes_from_file(file_obj)

        if errors:
            messages.warning(self.request, f"Processed {count} schemes with errors: {errors[:5]}...") # Limit errors
        else:
            messages.success(self.request, f"Successfully imported/updated {count} schemes.")

        return super().form_valid(form)

class NAVUploadView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'products/upload_nav.html'
    form_class = NAVUploadForm
    success_url = reverse_lazy('products:scheme_list') # Redirect to list for now

    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN

    def form_valid(self, form):
        file_obj = self.request.FILES['file']
        count, errors = import_navs_from_file(file_obj)

        if errors:
             messages.warning(self.request, f"Processed {count} NAV records with errors: {errors[:5]}...")
        else:
             messages.success(self.request, f"Successfully imported {count} NAV records.")

        return super().form_valid(form)

class DownloadSchemeSampleView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN

    def get(self, request, *args, **kwargs):
        excel_file = create_excel_sample_file(SCHEME_HEADERS, SCHEME_CHOICES)
        response = HttpResponse(
            excel_file.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="scheme_import_sample.xlsx"'
        return response

class DownloadNAVSampleView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN

    def get(self, request, *args, **kwargs):
        excel_file = create_excel_sample_file(NAV_HEADERS, NAV_CHOICES)
        response = HttpResponse(
            excel_file.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="nav_import_sample.xlsx"'
        return response

class AMCMasterView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = AMC
    template_name = 'products/amc_list.html'
    context_object_name = 'amcs'
    ordering = ['name']

    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN or self.request.user.is_staff

@login_required
@require_POST
def toggle_amc_status(request, pk):
    if not (request.user.user_type == User.Types.ADMIN or request.user.is_staff):
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('products:amc_list')

    amc = get_object_or_404(AMC, pk=pk)
    amc.is_active = not amc.is_active
    amc.save()
    status = "Active" if amc.is_active else "Inactive"
    messages.success(request, f"AMC {amc.name} is now {status}.")
    return redirect('products:amc_list')

@login_required
@require_POST
def update_amc_name(request, pk):
    if not (request.user.user_type == User.Types.ADMIN or request.user.is_staff):
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('products:amc_list')

    amc = get_object_or_404(AMC, pk=pk)
    new_name = request.POST.get('name')
    if new_name:
        amc.name = new_name
        amc.save()
        messages.success(request, f"AMC name updated to {amc.name}.")
    else:
        messages.error(request, "Name cannot be empty.")

    return redirect('products:amc_list')

class DownloadSchemeMasterReportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN or self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        schemes = Scheme.objects.all().select_related('amc', 'category')

        # Convert queryset to list of dicts with all fields
        data = []
        for scheme in schemes:
            item = {
                'ID': scheme.id,
                'AMC': scheme.amc.name if scheme.amc else '',
                'AMC Code': scheme.amc.code if scheme.amc else '',
                'Category': scheme.category.name if scheme.category else '',
                'Category Code': scheme.category.code if scheme.category else '',
                'Name': scheme.name,
                'ISIN': scheme.isin,
                'Scheme Code': scheme.scheme_code,
                'Unique No': scheme.unique_no,
                'RTA Scheme Code': scheme.rta_scheme_code,
                'AMC Scheme Code': scheme.amc_scheme_code,
                'AMFI Code': scheme.amfi_code,
                'Scheme Type': scheme.scheme_type,
                'Scheme Plan': scheme.scheme_plan,
                'Purchase Allowed': scheme.purchase_allowed,
                'Purchase Transaction Mode': scheme.purchase_transaction_mode,
                'Min Purchase Amount': scheme.min_purchase_amount,
                'Additional Purchase Amount': scheme.additional_purchase_amount,
                'Max Purchase Amount': scheme.max_purchase_amount,
                'Purchase Amount Multiplier': scheme.purchase_amount_multiplier,
                'Purchase Cutoff Time': scheme.purchase_cutoff_time,
                'Redemption Allowed': scheme.redemption_allowed,
                'Redemption Transaction Mode': scheme.redemption_transaction_mode,
                'Min Redemption Qty': scheme.min_redemption_qty,
                'Redemption Qty Multiplier': scheme.redemption_qty_multiplier,
                'Max Redemption Qty': scheme.max_redemption_qty,
                'Min Redemption Amount': scheme.min_redemption_amount,
                'Max Redemption Amount': scheme.max_redemption_amount,
                'Redemption Amount Multiple': scheme.redemption_amount_multiple,
                'Redemption Cutoff Time': scheme.redemption_cutoff_time,
                'SIP Allowed': scheme.is_sip_allowed,
                'STP Allowed': scheme.is_stp_allowed,
                'SWP Allowed': scheme.is_swp_allowed,
                'Switch Allowed': scheme.is_switch_allowed,
                'Start Date': scheme.start_date,
                'End Date': scheme.end_date,
                'Reopening Date': scheme.reopening_date,
                'Face Value': scheme.face_value,
                'Settlement Type': scheme.settlement_type,
                'RTA Agent Code': scheme.rta_agent_code,
                'AMC Active Flag': scheme.amc_active_flag,
                'Dividend Reinvestment Flag': scheme.dividend_reinvestment_flag,
                'AMC Ind': scheme.amc_ind,
                'Exit Load Flag': scheme.exit_load_flag,
                'Exit Load': scheme.exit_load,
                'Lock-in Period Flag': scheme.lock_in_period_flag,
                'Lock-in Period': scheme.lock_in_period,
                'Channel Partner Code': scheme.channel_partner_code,
                'Created At': scheme.created_at.replace(tzinfo=None) if scheme.created_at else None,
                'Updated At': scheme.updated_at.replace(tzinfo=None) if scheme.updated_at else None,
            }
            data.append(item)

        df = pd.DataFrame(data)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = f"Scheme_Master_Report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        df.to_excel(response, index=False)
        return response
