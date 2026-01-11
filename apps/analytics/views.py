import json
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, F

from .models import Goal, GoalMapping
from .forms import GoalForm, GoalMappingFormSet
from apps.users.models import User
from apps.reconciliation.models import Holding

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
                'action_url': str(reverse_lazy('goal_detail', kwargs={'pk': goal.pk})),
                'edit_url': str(reverse_lazy('goal_update', kwargs={'pk': goal.pk}))
            })

        context['grid_data_json'] = json.dumps(data)
        return context

class GoalCreateView(LoginRequiredMixin, CreateView):
    model = Goal
    form_class = GoalForm
    template_name = 'analytics/goal_form.html'
    success_url = reverse_lazy('goal_list')

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
    success_url = reverse_lazy('goal_list')

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
    success_url = reverse_lazy('goal_list')
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
