import json
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, F
from apps.analytics.models import CASUpload, ExternalHolding
from apps.analytics.forms import CASUploadForm
from apps.analytics.services.cas_parser import CASParser

from .models import Goal, GoalMapping
from .forms import GoalForm, GoalMappingFormSet
from apps.users.models import User, InvestorProfile
from apps.reconciliation.models import Holding

import logging
logger = logging.getLogger(__name__)

# --- Goal Views (Restored) ---

class GoalListView(LoginRequiredMixin, ListView):
    model = Goal
    template_name = 'analytics/goal_list.html'
    context_object_name = 'goals'

    def get_queryset(self):
        user = self.request.user
        qs = Goal.objects.none()

        if user.user_type == User.Types.INVESTOR:
            qs = Goal.objects.filter(investor__user=user)
        elif user.user_type == User.Types.DISTRIBUTOR:
            qs = Goal.objects.filter(investor__distributor__user=user)
        elif user.user_type == User.Types.ADMIN:
            qs = Goal.objects.all()

        return qs.select_related('investor', 'investor__user').prefetch_related('mappings', 'mappings__holding')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        goals = self.get_queryset()

        data = []
        for goal in goals:
            current_val = goal.current_value
            achieved = goal.achievement_percentage

            data.append({
                'id': goal.id,
                'name': goal.name,
                'investor': goal.investor.user.name or goal.investor.user.username,
                'target_amount': float(goal.target_amount),
                'current_value': float(current_val),
                'achieved_pct': float(achieved),
                'target_date': goal.target_date.strftime('%Y-%m-%d'),
                'category': goal.get_category_display(),
                'action_url': str(reverse_lazy('analytics:goal_detail', kwargs={'pk': goal.pk})),
                'edit_url': str(reverse_lazy('analytics:goal_update', kwargs={'pk': goal.pk}))
            })

        context['grid_data_json'] = json.dumps(data)
        return context

class GoalCreateView(LoginRequiredMixin, CreateView):
    model = Goal
    form_class = GoalForm
    template_name = 'analytics/goal_form.html'
    success_url = reverse_lazy('analytics:goal_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Create New Goal"
        if self.request.POST:
            context['mappings'] = GoalMappingFormSet(self.request.POST)
        else:
            context['mappings'] = GoalMappingFormSet()

        # Dynamically populate holdings for the formset
        # NOTE: In CreateView, if the user is a Distributor, they select the investor in the form.
        # This makes it hard to filter holdings server-side for the initial render without JS.
        # For Investor, we know the user.
        user = self.request.user
        holdings = Holding.objects.none()
        if user.user_type == User.Types.INVESTOR:
            holdings = Holding.objects.filter(investor__user=user).select_related('scheme')

        # We need to manually update the queryset for the empty form in the formset
        # and any bound forms if POST failed (handled in form_valid/invalid logic usually,
        # but needed here for initial render)
        for form in context['mappings'].forms:
            form.fields['holding'].queryset = holdings

        # Pass holdings for JS
        context['investor_holdings'] = holdings

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        mappings = context['mappings']

        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.user = self.request.user

            # If investor creating own goal
            if self.request.user.user_type == User.Types.INVESTOR:
                self.object.investor = self.request.user.investor_profile

            # If distributor, the investor is in self.object.investor from the form

            self.object.save()

            # Re-set querysets for validation to work (otherwise 'Select a valid choice' error)
            # This is critical because we set queryset=none() in Form __init__
            target_investor = self.object.investor
            valid_holdings = Holding.objects.filter(investor=target_investor)
            for m_form in mappings:
                m_form.fields['holding'].queryset = valid_holdings

            if mappings.is_valid():
                mappings.instance = self.object
                mappings.save()
            else:
                return self.form_invalid(form)

        messages.success(self.request, "Goal created successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        # We need to ensure the formset forms have the correct queryset when re-rendering
        # This is tricky because 'investor' might be in request.POST
        return super().form_invalid(form)

class GoalUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Goal
    form_class = GoalForm
    template_name = 'analytics/goal_form.html'
    success_url = reverse_lazy('analytics:goal_list')

    def test_func(self):
        goal = self.get_object()
        user = self.request.user
        if user.user_type == User.Types.ADMIN: return True
        if user.user_type == User.Types.INVESTOR and goal.investor.user == user: return True
        if user.user_type == User.Types.DISTRIBUTOR and goal.investor.distributor.user == user: return True
        return False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Update Goal: {self.object.name}"

        # Determine valid holdings for this goal's investor
        holdings = Holding.objects.filter(investor=self.object.investor).select_related('scheme')
        context['investor_holdings'] = holdings

        if self.request.POST:
            context['mappings'] = GoalMappingFormSet(self.request.POST, instance=self.object)
        else:
            context['mappings'] = GoalMappingFormSet(instance=self.object)

        # Populate queryset for all forms in formset
        for form in context['mappings'].forms:
            form.fields['holding'].queryset = holdings

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        mappings = context['mappings']

        with transaction.atomic():
            self.object = form.save()

            # Re-set querysets for validation
            holdings = Holding.objects.filter(investor=self.object.investor)
            for m_form in mappings:
                m_form.fields['holding'].queryset = holdings

            if mappings.is_valid():
                mappings.save()
            else:
                return self.form_invalid(form)

        messages.success(self.request, "Goal updated successfully.")
        return super().form_valid(form)

class GoalDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Goal
    template_name = 'analytics/goal_detail.html'
    context_object_name = 'goal'

    def test_func(self):
        goal = self.get_object()
        user = self.request.user
        if user.user_type == User.Types.ADMIN: return True
        if user.user_type == User.Types.INVESTOR and goal.investor.user == user: return True
        if user.user_type == User.Types.DISTRIBUTOR and goal.investor.distributor.user == user: return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mappings = self.object.mappings.select_related('holding', 'holding__scheme').all()

        mapping_data = []
        for m in mappings:
            mapping_data.append({
                'scheme': m.holding.scheme.name,
                'folio': m.holding.folio_number,
                'holding_value': float(m.holding.current_value or 0),
                'allocation_pct': float(m.allocation_percentage),
                'allocated_value': float((m.holding.current_value or 0) * (m.allocation_percentage / 100))
            })

        context['mapping_grid_json'] = json.dumps(mapping_data)
        return context

class GoalDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Goal
    success_url = reverse_lazy('analytics:goal_list')
    template_name = 'analytics/goal_confirm_delete.html'

    def test_func(self):
        goal = self.get_object()
        user = self.request.user
        if user.user_type == User.Types.ADMIN: return True
        if user.user_type == User.Types.INVESTOR and goal.investor.user == user: return True
        if user.user_type == User.Types.DISTRIBUTOR and goal.investor.distributor.user == user: return True
        return False

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Goal deleted successfully.")
        return super().delete(request, *args, **kwargs)

# --- CAS Views (Added) ---

class CASUploadView(LoginRequiredMixin, CreateView):
    model = CASUpload
    form_class = CASUploadForm
    template_name = 'analytics/cas_upload.html'
    success_url = reverse_lazy('analytics:cas_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        password = form.cleaned_data['password']

        user = self.request.user
        investor_profile = None

        if hasattr(user, 'investor_profile'):
            investor_profile = user.investor_profile
        else:
            # For Admin/Distributor, investor is selected in the form
            investor_profile = form.cleaned_data.get('investor')
            if not investor_profile:
                 # Fallback if form field missing or empty (should be required by Django form if field exists)
                 form.add_error('investor', "Please select an investor.")
                 return self.form_invalid(form)

        self.object = form.save(commit=False)
        self.object.uploaded_by = user
        self.object.investor = investor_profile
        self.object.save()

        # Trigger Parsing
        try:
            parser = CASParser(self.object.file.path, password=password)
            holdings_data = parser.parse()

            for data in holdings_data:
                ExternalHolding.objects.create(
                    cas_upload=self.object,
                    investor=investor_profile,
                    **data
                )

            self.object.status = CASUpload.STATUS_PROCESSED
            self.object.save()
            messages.success(self.request, "CAS uploaded and parsed successfully.")

        except Exception as e:
            self.object.status = CASUpload.STATUS_FAILED
            self.object.error_log = str(e)
            self.object.save()
            messages.error(self.request, f"Failed to parse CAS: {str(e)}")

        return redirect(self.success_url)

class CASListView(LoginRequiredMixin, ListView):
    model = CASUpload
    template_name = 'analytics/cas_list.html'
    context_object_name = 'cas_uploads'

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'INVESTOR':
            return CASUpload.objects.filter(investor=user.investor_profile)
        elif user.user_type == 'DISTRIBUTOR':
            return CASUpload.objects.filter(investor__distributor__user=user)
        elif user.user_type == 'RM':
             return CASUpload.objects.filter(investor__distributor__rm__user=user)
        return CASUpload.objects.all()

class ExternalHoldingListView(LoginRequiredMixin, ListView):
    model = ExternalHolding
    template_name = 'analytics/external_holdings.html'
    context_object_name = 'holdings'

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'INVESTOR':
            return ExternalHolding.objects.filter(investor=user.investor_profile)
        elif user.user_type == 'DISTRIBUTOR':
            return ExternalHolding.objects.filter(investor__distributor__user=user)
        elif user.user_type == 'RM':
             return ExternalHolding.objects.filter(investor__distributor__rm__user=user)
        return ExternalHolding.objects.all()
