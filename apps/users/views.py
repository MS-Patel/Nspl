from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, CreateView
from django.contrib.auth import get_user_model
from .models import RMProfile, DistributorProfile, InvestorProfile
from .forms import RMCreationForm, DistributorCreationForm, InvestorCreationForm

User = get_user_model()

# --- Authentication & Dashboard Views ---

class CustomLoginView(LoginView):
    template_name = 'auth/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.user_type == User.Types.RM:
            return reverse_lazy('rm_dashboard')
        elif user.user_type == User.Types.DISTRIBUTOR:
            return reverse_lazy('distributor_dashboard')
        elif user.user_type == User.Types.INVESTOR:
            return reverse_lazy('investor_dashboard')
        return reverse_lazy('admin_dashboard')

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')

# --- Mixins for Role-Based Access ---

class IsAdminMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.user_type == User.Types.ADMIN

class IsRMMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.user_type == User.Types.RM

class IsDistributorMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.user_type == User.Types.DISTRIBUTOR

class IsAdminOrRMMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.user_type == User.Types.ADMIN or
            self.request.user.user_type == User.Types.RM
        )

# --- Dashboard Views ---

class AdminDashboardView(LoginRequiredMixin, IsAdminMixin, TemplateView):
    template_name = 'dashboard/admin.html'

class RMDashboardView(LoginRequiredMixin, IsRMMixin, TemplateView):
    template_name = 'dashboard/rm.html'

class DistributorDashboardView(LoginRequiredMixin, IsDistributorMixin, TemplateView):
    template_name = 'dashboard/distributor.html'

class InvestorDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/investor.html'

# --- User Management Views (The Permissions Layer) ---

# 1. RM Management (Admin Only)
class RMListView(LoginRequiredMixin, IsAdminMixin, ListView):
    model = RMProfile
    template_name = 'users/rm_list.html'
    context_object_name = 'rms'

class RMCreateView(LoginRequiredMixin, IsAdminMixin, CreateView):
    model = User # Form handles User + Profile
    form_class = RMCreationForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('rm_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Create Relationship Manager"
        return context

# 2. Distributor Management (Admin & RM)
class DistributorListView(LoginRequiredMixin, IsAdminOrRMMixin, ListView):
    model = DistributorProfile
    template_name = 'users/distributor_list.html'
    context_object_name = 'distributors'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == User.Types.RM:
            # RM sees only their assigned distributors
            return qs.filter(rm__user=user)
        return qs # Admin sees all

class DistributorCreateView(LoginRequiredMixin, IsAdminOrRMMixin, CreateView):
    form_class = DistributorCreationForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('distributor_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['rm_user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Create Distributor"
        return context

# 3. Investor Management (Admin, RM, Distributor)
# Logic: Distributor sees own; RM sees investors of their distributors; Admin sees all.

class InvestorListView(LoginRequiredMixin, ListView):
    model = InvestorProfile
    template_name = 'users/investor_list.html'
    context_object_name = 'investors'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == User.Types.DISTRIBUTOR:
            return qs.filter(distributor__user=user)
        elif user.user_type == User.Types.RM:
            return qs.filter(distributor__rm__user=user)
        elif user.user_type == User.Types.ADMIN:
            return qs
        return qs.none() # Investors can't see list of investors

class InvestorCreateView(LoginRequiredMixin, IsDistributorMixin, CreateView):
    # Currently restricting creation to Distributors only as per typical workflow
    # Admin/RM creation can be added if needed
    form_class = InvestorCreationForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('investor_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['distributor_user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Onboard Investor"
        return context
