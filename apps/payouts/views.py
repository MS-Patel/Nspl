from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, DetailView, CreateView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import get_user_model
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

    def form_valid(self, form):
        self.object = form.save()
        try:
            # Trigger processing immediately (or move to Celery/background task)
            process_brokerage_import(self.object)
            messages.success(self.request, "Brokerage files uploaded and processed successfully.")
        except Exception as e:
            messages.error(self.request, f"Error processing files: {e}")
        return redirect(self.success_url)

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
