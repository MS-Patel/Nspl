from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView, CreateView, View, UpdateView, DeleteView
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Payout, BrokerageImport, BrokerageTransaction, DistributorCategory
from .forms import BrokerageUploadForm
from .utils import process_brokerage_import, reprocess_brokerage_import
from apps.products.models import Scheme
import ast
import pandas as pd
import io
import math

User = get_user_model()

class PayoutDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'payouts/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Filter logic for dashboard widgets
        if user.user_type == User.Types.ADMIN:
            context['latest_imports'] = BrokerageImport.objects.all()[:5]
            context['latest_payouts'] = Payout.objects.all()[:5]
        elif user.user_type == User.Types.RM:
            context['latest_imports'] = [] # RM shouldn't see raw imports
            context['latest_payouts'] = Payout.objects.filter(distributor__rm__user=user)[:5]
        elif user.user_type == User.Types.DISTRIBUTOR:
             context['latest_imports'] = []
             context['latest_payouts'] = Payout.objects.filter(distributor__user=user)[:5]

        return context

class BrokerageUploadView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    template_name = 'payouts/upload.html'
    model = BrokerageImport
    form_class = BrokerageUploadForm
    success_url = '/payouts/dashboard/'

    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN


    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()

        if form.is_valid():
            return self.form_valid(form)

        # Form is invalid. Check for duplicates and overwrite request.
        try:
            month = request.POST.get('month')
            year = request.POST.get('year')
            overwrite = request.POST.get('overwrite')

            duplicate_exists = False
            if month and year:
                duplicate_exists = BrokerageImport.objects.filter(month=month, year=year).exists()

            if duplicate_exists:
                if overwrite == 'true':
                    # Attempt safe overwrite
                    try:
                        with transaction.atomic():
                            # Delete existing import
                            BrokerageImport.objects.filter(month=month, year=year).delete()

                            # Re-validate form against new state (duplicate gone)
                            form_retry = self.get_form()
                            if form_retry.is_valid():
                                return self.form_valid(form_retry)
                            else:
                                # Still invalid (e.g. file errors), rollback deletion
                                raise ValueError("Form invalid during overwrite")
                    except ValueError:
                        # Transaction rolled back, old data restored.
                        # Return original errors (which include unique error + file errors)
                        return self.form_invalid(form)
                else:
                    # Duplicate exists, no overwrite requested -> 409
                    return JsonResponse({
                        'status': 'conflict',
                        'message': f'Brokerage Import for {month}/{year} already exists.'
                    }, status=409)
        except Exception as e:
            # If unexpected error, fall through to standard form_invalid
            pass

        return self.form_invalid(form)

    def is_ajax(self):
        return (
            self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or
            self.request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest' or
            self.request.accepts('application/json')
        )

    def form_valid(self, form):
        self.object = form.save()
        try:
            # Trigger processing immediately (or move to Celery/background task)
            process_brokerage_import(self.object)

            # If AJAX request, return JSON success
            if self.is_ajax():
                 return JsonResponse({
                    'status': 'success',
                    'message': "Brokerage files uploaded and processed successfully.",
                    'redirect_url': self.success_url
                })

            messages.success(self.request, "Brokerage files uploaded and processed successfully.")
        except Exception as e:
            if self.is_ajax():
                 return JsonResponse({
                    'status': 'error',
                    'message': f"Error processing files: {str(e)}"
                }, status=400)
            messages.error(self.request, f"Error processing files: {e}")

        return redirect(self.success_url)

    def form_invalid(self, form):
        if self.is_ajax():
            return JsonResponse({
                'status': 'error',
                'errors': form.errors
            }, status=400)
        return super().form_invalid(form)

class PayoutListView(LoginRequiredMixin, ListView):
    model = Payout
    template_name = 'payouts/payout_list.html'
    context_object_name = 'object_list'

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.user_type == User.Types.ADMIN:
            return qs
        elif user.user_type == User.Types.RM:
            return qs.filter(distributor__rm__user=user)
        elif user.user_type == User.Types.DISTRIBUTOR:
            return qs.filter(distributor__user=user)
        return qs.none()

class PayoutDetailView(LoginRequiredMixin, DetailView):
    model = Payout
    template_name = 'payouts/payout_detail.html'

    def get_queryset(self):
        # Ensure IDOR protection
        user = self.request.user
        qs = super().get_queryset()
        if user.user_type == User.Types.ADMIN:
            return qs
        elif user.user_type == User.Types.RM:
            return qs.filter(distributor__rm__user=user)
        elif user.user_type == User.Types.DISTRIBUTOR:
            return qs.filter(distributor__user=user)
        return qs.none()

    def get(self, request, *args, **kwargs):
        is_ajax = (
            request.headers.get('x-requested-with') == 'XMLHttpRequest' or
            request.GET.get('format') == 'json'
        )

        if is_ajax:
            self.object = self.get_object()

            # Efficient Filtering
            qs = BrokerageTransaction.objects.filter(
                import_file=self.object.brokerage_import,
                distributor=self.object.distributor
            )

            # Search logic
            keyword = request.GET.get('keyword', '')
            if keyword:
                qs = qs.filter(
                    Q(investor_name__icontains=keyword) |
                    Q(folio_number__icontains=keyword) |
                    Q(scheme_name__icontains=keyword)
                )

            # Sorting logic
            qs = qs.order_by('-transaction_date', 'id')

            # Pagination
            try:
                limit = int(request.GET.get('limit', 10))
                page_num = int(request.GET.get('page', 0)) + 1
            except ValueError:
                limit = 10
                page_num = 1

            paginator = Paginator(qs, limit)
            page = paginator.get_page(page_num)

            data = []
            for txn in page.object_list:
                amount_val = float(txn.amount)
                brokerage_val = float(txn.brokerage_amount)

                if math.isnan(amount_val):
                    amount_val = 0.0
                if math.isnan(brokerage_val):
                    brokerage_val = 0.0

                data.append({
                    'date': txn.transaction_date,
                    'source': txn.source,
                    'investor': txn.investor_name,
                    'folio': txn.folio_number,
                    'scheme': txn.scheme_name,
                    'amount': amount_val,
                    'brokerage': brokerage_val,
                    'remark': txn.mapping_remark
                })

            return JsonResponse({
                'data': data,
                'total': paginator.count
            })

        return super().get(request, *args, **kwargs)

class BrokerageImportListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = BrokerageImport
    template_name = 'payouts/import_list.html'
    context_object_name = 'object_list'

    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN

class BrokerageImportDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = BrokerageImport
    template_name = 'payouts/import_detail.html'

    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # We no longer load all transactions here to improve performance.
        # Data is fetched via AJAX.
        return context

    def get(self, request, *args, **kwargs):
        is_ajax = (
            request.headers.get('x-requested-with') == 'XMLHttpRequest' or
            request.GET.get('format') == 'json'
        )

        if is_ajax:
            self.object = self.get_object()
            qs = self.object.transactions.all()

            # Search
            keyword = request.GET.get('keyword', '')
            if keyword:
                qs = qs.filter(
                    Q(investor_name__icontains=keyword) |
                    Q(folio_number__icontains=keyword) |
                    Q(scheme_name__icontains=keyword)
                )

            # Filter by Status
            status = request.GET.get('status', 'all')
            if status == 'mapped':
                qs = qs.filter(is_mapped=True)
            elif status == 'unmapped':
                qs = qs.filter(is_mapped=False)

            # Sorting
            # Grid.js sends ?sort=... sometimes, but let's stick to default ordering first
            # The previous logic ordered by 'is_mapped', 'id'.
            qs = qs.order_by('is_mapped', 'id')

            # Pagination
            try:
                limit = int(request.GET.get('limit', 10))
                page_num = int(request.GET.get('page', 0)) + 1
            except ValueError:
                limit = 10
                page_num = 1

            paginator = Paginator(qs, limit)
            page = paginator.get_page(page_num)

            data = []
            for txn in page.object_list:
                raw = txn.raw_data
                if isinstance(raw, str):
                    try:
                        raw = ast.literal_eval(raw)
                    except:
                        raw = {}
                else:
                    raw = txn.raw_data or {}

                display_pan = raw.get('InvPAN') or raw.get('PAN_NO') or raw.get('PAN_NUMBER') or '-'

                amount_val = float(txn.amount)
                brokerage_val = float(txn.brokerage_amount)

                if math.isnan(amount_val):
                    amount_val = 0.0
                if math.isnan(brokerage_val):
                    brokerage_val = 0.0

                data.append({
                    'id': txn.id,
                    'status': txn.is_mapped,
                    'source': txn.source,
                    'investor': txn.investor_name,
                    'folio': txn.folio_number,
                    'pan': display_pan,
                    'scheme': txn.scheme_name,
                    'amount': amount_val,
                    'brokerage': brokerage_val,
                    'remark': txn.mapping_remark
                })

            return JsonResponse({
                'data': data,
                'total': paginator.count
            })

        return super().get(request, *args, **kwargs)

class ReprocessImportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN

    def post(self, request, pk, *args, **kwargs):
        brokerage_import = get_object_or_404(BrokerageImport, pk=pk)
        try:
            mapped_count = reprocess_brokerage_import(brokerage_import)
            if mapped_count > 0:
                messages.success(request, f"Successfully mapped {mapped_count} transactions and recalculated payouts.")
            else:
                messages.info(request, "Reprocessing complete. No new transactions were mapped.")
        except Exception as e:
            messages.error(request, f"Error reprocessing import: {str(e)}")

        return redirect('payouts:import_detail', pk=pk)


class ExportPayoutReportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN

    def get(self, request, pk, *args, **kwargs):
        brokerage_import = get_object_or_404(BrokerageImport, pk=pk)
        payouts = brokerage_import.payouts.select_related('distributor', 'distributor__user').all()

        data = []
        for p in payouts:
            data.append({
                'Distributor Name': p.distributor.user.get_full_name() or p.distributor.user.username,
                'Broker Code': p.distributor.broker_code,
                'ARN Number': p.distributor.arn_number,
                'PAN': p.distributor.pan,
                'Total AUM': p.total_aum,
                'Category': p.category,
                'Gross Brokerage': p.gross_brokerage,
                'Share %': p.share_percentage,
                'Payable Amount': p.payable_amount,
                'Status': p.status
            })

        df = pd.DataFrame(data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Payouts')

        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"payout_report_{brokerage_import.id}.xlsx"
        response['Content-Disposition'] = f'attachment; filename={filename}'

        return response


class ExportAMCPayoutReportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN

    def get(self, request, pk, *args, **kwargs):
        brokerage_import = get_object_or_404(BrokerageImport, pk=pk)

        # 1. Fetch Transactions
        transactions = brokerage_import.transactions.select_related('distributor').all()

        # 2. Fetch Payouts to get share percentage
        # Map distributor_id -> share_percentage
        payouts = brokerage_import.payouts.all()
        distributor_share_map = {p.distributor_id: p.share_percentage for p in payouts}

        # 3. Pre-fetch Schemes for lookup
        # We can fetch all schemes and create a map: name -> amc_name
        schemes = Scheme.objects.select_related('amc').all()
        scheme_map = {s.name.lower(): s.amc.name for s in schemes}

        amc_stats = {} # amc_name -> {'gross': 0, 'payable': 0}

        for txn in transactions:
            amc_name = "Unknown"

            # Try matching by name
            if txn.scheme_name:
                scheme_name_lower = txn.scheme_name.lower().strip()
                if scheme_name_lower in scheme_map:
                    amc_name = scheme_map[scheme_name_lower]
                else:
                    # Fuzzy / Partial Match Attempt
                    # Many times RTA name is slightly different or contains extra spaces
                    # This is basic, but helps catch some
                    pass

            if amc_name not in amc_stats:
                amc_stats[amc_name] = {'gross': 0.0, 'payable': 0.0}

            gross = float(txn.brokerage_amount)
            if math.isnan(gross): gross = 0.0

            share_pct = float(distributor_share_map.get(txn.distributor_id, 0.0))
            payable = gross * (share_pct / 100.0)

            amc_stats[amc_name]['gross'] += gross
            amc_stats[amc_name]['payable'] += payable

        # Create DataFrame
        data = []
        for amc, stats in amc_stats.items():
            data.append({
                'AMC Name': amc,
                'Gross Brokerage': stats['gross'],
                'Payable Amount': stats['payable']
            })

        df = pd.DataFrame(data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='AMC Payouts')

        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"amc_payout_report_{brokerage_import.id}.xlsx"
        response['Content-Disposition'] = f'attachment; filename={filename}'

        return response


class DistributorCategoryListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = DistributorCategory
    template_name = 'payouts/category_list.html'
    context_object_name = 'object_list'

    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN

class DistributorCategoryCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = DistributorCategory
    template_name = 'payouts/category_form.html'
    fields = ['name', 'min_aum', 'max_aum', 'share_percentage']
    success_url = reverse_lazy('payouts:category_list')

    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN

class DistributorCategoryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = DistributorCategory
    template_name = 'payouts/category_form.html'
    fields = ['name', 'min_aum', 'max_aum', 'share_percentage']
    success_url = reverse_lazy('payouts:category_list')

    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN

class DistributorCategoryDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = DistributorCategory
    template_name = 'payouts/category_confirm_delete.html'
    success_url = reverse_lazy('payouts:category_list')

    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN

class ExportTransactionReportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN

    def get(self, request, pk, *args, **kwargs):
        brokerage_import = get_object_or_404(BrokerageImport, pk=pk)
        transactions = brokerage_import.transactions.select_related('distributor', 'distributor__user').all()

        data = []
        for txn in transactions:
            data.append({
                'Transaction Date': txn.transaction_date,
                'Source': txn.source,
                'Investor Name': txn.investor_name,
                'Folio Number': txn.folio_number,
                'Scheme Name': txn.scheme_name,
                'Amount': txn.amount,
                'Brokerage Amount': txn.brokerage_amount,
                'Status': 'Mapped' if txn.is_mapped else 'Unmapped',
                'Mapped Distributor': txn.distributor.user.username if txn.distributor else '',
                'Remark': txn.mapping_remark
            })

        df = pd.DataFrame(data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Transactions')

        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"transaction_report_{brokerage_import.id}.xlsx"
        response['Content-Disposition'] = f'attachment; filename={filename}'

        return response
