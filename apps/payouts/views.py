from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, DetailView, CreateView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Payout, BrokerageImport, BrokerageTransaction, DistributorCategory
from .forms import BrokerageUploadForm
from .utils import process_brokerage_import

class PayoutDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'payouts/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['latest_imports'] = BrokerageImport.objects.all()[:5]
        context['latest_payouts'] = Payout.objects.all()[:5]
        return context

class BrokerageUploadView(LoginRequiredMixin, CreateView):
    template_name = 'payouts/upload.html'
    model = BrokerageImport
    form_class = BrokerageUploadForm
    success_url = '/payouts/dashboard/'

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

class PayoutDetailView(LoginRequiredMixin, DetailView):
    model = Payout
    template_name = 'payouts/payout_detail.html'

class BrokerageImportListView(LoginRequiredMixin, ListView):
    model = BrokerageImport
    template_name = 'payouts/import_list.html'
    context_object_name = 'object_list'

class BrokerageImportDetailView(LoginRequiredMixin, DetailView):
    model = BrokerageImport
    template_name = 'payouts/import_detail.html'
