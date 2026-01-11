from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView
from django.contrib import messages
from django.db import transaction
import json

from .models import CommissionRule
from .forms import CommissionRuleForm, CommissionTierFormSet
from apps.users.models import User

class IsAdminMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.user_type == User.Types.ADMIN

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
                'action_url': reverse_lazy('payout_rule_update', kwargs={'pk': rule.pk})
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
