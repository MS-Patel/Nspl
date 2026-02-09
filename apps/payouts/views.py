from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, DetailView, CreateView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.db import transaction
from .models import Payout, BrokerageImport, BrokerageTransaction, DistributorCategory
from .forms import BrokerageUploadForm
from .utils import process_brokerage_import

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
