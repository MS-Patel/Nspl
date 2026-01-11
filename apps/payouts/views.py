from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
import json
import openpyxl

from .models import CommissionRule, Payout, PayoutDetail
from .forms import CommissionRuleForm, CommissionTierFormSet
from apps.users.models import User

class IsAdminMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.user_type == User.Types.ADMIN

class IsDistributorMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.user_type == User.Types.DISTRIBUTOR

class CommissionRuleListView(LoginRequiredMixin, IsAdminMixin, ListView):
    model = CommissionRule
    template_name = 'payouts/rule_list.html'
    context_object_name = 'rules'

    def get_queryset(self):
        return CommissionRule.objects.select_related('category', 'amc').prefetch_related('tiers')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = []
        for rule in self.get_queryset():
            tiers = rule.tiers.all()
            tiers_str = ", ".join([f"{t.rate}% (> {t.min_aum})" for t in tiers])
            data.append({
                'id': rule.id,
                'category': rule.category.name,
                'amc': rule.amc.name if rule.amc else 'All AMCs',
                'tiers': tiers_str,
                'action_url': str(reverse_lazy('payout_rule_update', kwargs={'pk': rule.pk}))
            })
        context['grid_data_json'] = json.dumps(data)
        return context

class CommissionRuleCreateView(LoginRequiredMixin, IsAdminMixin, CreateView):
    model = CommissionRule
    form_class = CommissionRuleForm
    template_name = 'payouts/rule_form.html'
    success_url = reverse_lazy('payout_rule_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Create Commission Rule"
        if self.request.POST:
            context['tiers'] = CommissionTierFormSet(self.request.POST)
        else:
            context['tiers'] = CommissionTierFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        tiers = context['tiers']
        with transaction.atomic():
            self.object = form.save()
            if tiers.is_valid():
                tiers.instance = self.object
                tiers.save()
            else:
                return self.form_invalid(form)
        messages.success(self.request, "Commission Rule Created Successfully")
        return super().form_valid(form)

class CommissionRuleUpdateView(LoginRequiredMixin, IsAdminMixin, UpdateView):
    model = CommissionRule
    form_class = CommissionRuleForm
    template_name = 'payouts/rule_form.html'
    success_url = reverse_lazy('payout_rule_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Edit Commission Rule"
        if self.request.POST:
            context['tiers'] = CommissionTierFormSet(self.request.POST, instance=self.object)
        else:
            context['tiers'] = CommissionTierFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        tiers = context['tiers']
        with transaction.atomic():
            self.object = form.save()
            if tiers.is_valid():
                tiers.save()
            else:
                return self.form_invalid(form)
        messages.success(self.request, "Commission Rule Updated Successfully")
        return super().form_valid(form)

class PayoutListView(LoginRequiredMixin, IsDistributorMixin, ListView):
    model = Payout
    template_name = 'payouts/payout_list.html'
    context_object_name = 'payouts'

    def get_queryset(self):
        return Payout.objects.filter(distributor=self.request.user).order_by('-period_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = []
        for payout in self.get_queryset():
            data.append({
                'period': payout.period_date.strftime('%B %Y'),
                'total_aum': float(payout.total_aum),
                'total_commission': float(payout.total_commission),
                'status': payout.get_status_display(),
                'action_url': str(reverse_lazy('payout_detail', kwargs={'pk': payout.pk}))
            })
        context['grid_data_json'] = json.dumps(data)
        return context

class PayoutDetailView(LoginRequiredMixin, IsDistributorMixin, DetailView):
    model = Payout
    template_name = 'payouts/payout_detail.html'
    context_object_name = 'payout'

    def get_queryset(self):
        # Ensure user can only see their own payouts
        return Payout.objects.filter(distributor=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        details = self.object.details.all()
        data = []
        for detail in details:
            data.append({
                'investor': detail.investor_name,
                'scheme': detail.scheme_name,
                'folio': detail.folio_number,
                'category': detail.category,
                'amc': detail.amc_name,
                'aum': float(detail.aum),
                'rate': float(detail.applied_rate),
                'commission': float(detail.commission_amount)
            })
        context['grid_data_json'] = json.dumps(data)
        return context

class PayoutExportView(LoginRequiredMixin, IsDistributorMixin, View):
    def get(self, request, pk, *args, **kwargs):
        payout = get_object_or_404(Payout, pk=pk, distributor=request.user)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=Payout_{payout.period_date.strftime("%Y_%m")}.xlsx'

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Payout Details"

        # Header
        headers = ["Investor Name", "Folio", "Scheme", "Category", "AMC", "AUM", "Rate (%)", "Commission"]
        ws.append(headers)

        for detail in payout.details.all():
            ws.append([
                detail.investor_name,
                detail.folio_number,
                detail.scheme_name,
                detail.category,
                detail.amc_name,
                detail.aum,
                detail.applied_rate,
                detail.commission_amount
            ])

        wb.save(response)
        return response
