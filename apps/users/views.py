from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, CreateView, DetailView, FormView, UpdateView
from django.contrib.auth import get_user_model
from django.db import transaction
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.views import View
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count, Sum
from django.db import models
from django.utils.crypto import get_random_string
from django.contrib.auth import login
from .models import RMProfile, DistributorProfile, InvestorProfile, BankAccount, Nominee, Document, OneTimePassword
from .utils.sms import send_sms_with_template
from .forms import (
    RMCreationForm, RMChangeForm, DistributorCreationForm, DistributorChangeForm,
    InvestorCreationForm, InvestorProfileForm,
    BankAccountFormSet, NomineeFormSet, DocumentForm, InvestorUploadForm, DistributorUploadForm,
    UserProfileForm, RMProfileUpdateForm, DistributorProfileUpdateForm, RMUploadForm
)
from .utils.parsers import import_investors_from_file, import_distributors_from_file, import_rms_from_file
from .services import validate_investor_for_bse
from apps.integration.bse_client import BSEStarMFClient
from apps.integration.utils import map_investor_to_bse_param_string
from apps.reconciliation.utils.valuation import calculate_portfolio_valuation
from apps.integration.sync_utils import sync_pending_mandates, sync_pending_orders, sync_sip_child_orders
from apps.investments.models import Order, SIP
from apps.reconciliation.models import Holding
from apps.core.utils.excel_generator import create_excel_sample_file
from apps.core.utils.sample_headers import (
    INVESTOR_HEADERS, INVESTOR_CHOICES,
    DISTRIBUTOR_HEADERS, DISTRIBUTOR_CHOICES,
    RM_HEADERS, RM_CHOICES
)
import logging
import json
import csv
import io

User = get_user_model()
logger = logging.getLogger(__name__)

# --- Authentication & Dashboard Views ---

class CustomLoginView(LoginView):
    template_name = 'auth/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.user_type == User.Types.RM:
            return reverse_lazy('users:rm_dashboard')
        elif user.user_type == User.Types.DISTRIBUTOR:
            return reverse_lazy('users:distributor_dashboard')
        elif user.user_type == User.Types.INVESTOR:
            return reverse_lazy('users:investor_dashboard')
        return reverse_lazy('users:admin_dashboard')

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('users:login')

class SendOTPView(View):
    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        if not username:
             return JsonResponse({'status': 'error', 'message': 'Username is required.'}, status=400)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
             return JsonResponse({'status': 'error', 'message': 'User not found.'}, status=404)

        if not user.is_active:
             return JsonResponse({'status': 'error', 'message': 'User account is inactive.'}, status=403)

        # Determine Mobile Number
        mobile = None
        if user.user_type == User.Types.RM and hasattr(user, 'rm_profile'):
             mobile = user.rm_profile.mobile
        elif user.user_type == User.Types.DISTRIBUTOR and hasattr(user, 'distributor_profile'):
             mobile = user.distributor_profile.mobile
        elif user.user_type == User.Types.INVESTOR and hasattr(user, 'investor_profile'):
             mobile = user.investor_profile.mobile

        if not mobile:
             return JsonResponse({'status': 'error', 'message': 'No mobile number linked to this account.'}, status=400)

        # Generate OTP
        otp = get_random_string(length=6, allowed_chars='0123456789')

        # Save OTP (Invalidate previous unused OTPs?)
        OneTimePassword.objects.create(user=user, otp=otp)

        # Send SMS
        context = {'otp': otp}
        # Assuming template name 'otp'
        sms_result = send_sms_with_template(mobile, 'otp', context)

        if isinstance(sms_result, dict) and sms_result.get('status') == 'error':
             return JsonResponse(sms_result, status=500)

        # Mask mobile number for response
        masked_mobile = f"{mobile[:2]}******{mobile[-2:]}" if len(mobile) > 4 else mobile

        return JsonResponse({'status': 'success', 'message': f'OTP sent to {masked_mobile}'})


class VerifyOTPLoginView(View):
    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        otp = request.POST.get('otp')

        if not username or not otp:
             return JsonResponse({'status': 'error', 'message': 'Username and OTP are required.'}, status=400)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
             return JsonResponse({'status': 'error', 'message': 'User not found.'}, status=404)

        # Verify OTP
        # Check for OTP created in last 10 minutes and not used
        ten_minutes_ago = timezone.now() - timezone.timedelta(minutes=10)
        valid_otp = OneTimePassword.objects.filter(
            user=user,
            otp=otp,
            is_used=False,
            created_at__gte=ten_minutes_ago
        ).first()

        if valid_otp:
            valid_otp.is_used = True
            valid_otp.save()

            # Log the user in
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)

            # Redirect URL logic (copied from CustomLoginView)
            success_url = reverse('users:admin_dashboard') # Default
            if user.user_type == User.Types.RM:
                success_url = reverse('users:rm_dashboard')
            elif user.user_type == User.Types.DISTRIBUTOR:
                success_url = reverse('users:distributor_dashboard')
            elif user.user_type == User.Types.INVESTOR:
                success_url = reverse('users:investor_dashboard')

            return JsonResponse({'status': 'success', 'redirect_url': success_url})
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid or expired OTP.'}, status=400)

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 1. Counts
        context['rm_count'] = RMProfile.objects.count()
        context['distributor_count'] = DistributorProfile.objects.count()
        context['investor_count'] = InvestorProfile.objects.count()

        # 2. Total AUM
        aum_agg = Holding.objects.aggregate(total_aum=Sum('current_value'))
        context['total_aum'] = aum_agg['total_aum'] or 0

        # 3. Recent Activity (e.g., Recent Orders)
        recent_orders = Order.objects.select_related('investor__user', 'scheme').order_by('-created_at')[:10]
        context['recent_orders'] = recent_orders

        return context

class RMDashboardView(LoginRequiredMixin, IsRMMixin, TemplateView):
    template_name = 'dashboard/rm.html'

class DistributorDashboardView(LoginRequiredMixin, IsDistributorMixin, TemplateView):
    template_name = 'dashboard/distributor.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # 1. Investors
        investors = InvestorProfile.objects.filter(distributor__user=user)
        context['investor_count'] = investors.count()

        # 2. AUM (Sum of Holdings for these investors)
        aum_agg = Holding.objects.filter(investor__in=investors).aggregate(total_aum=Sum('current_value'))
        context['total_aum'] = aum_agg['total_aum'] or 0

        # 3. Active SIPs
        context['active_sip_count'] = SIP.objects.filter(investor__in=investors, status='ACTIVE').count()

        # 4. Recent Orders (Limit 5)
        recent_orders = Order.objects.filter(investor__in=investors).select_related('investor__user', 'scheme').order_by('-created_at')[:5]
        context['recent_orders'] = recent_orders

        return context

class InvestorDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/investor.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Determine the Investor Profile
        investor_profile = None
        if user.user_type == User.Types.INVESTOR:
            # Handle potential DoesNotExist if profile creation failed (though it shouldn't)
            try:
                investor_profile = user.investor_profile

                # Sync SIPs and Orders for this investor (Mandates are synced in Detail View)
                # Since Dashboard usually shows high level info, syncing SIP child orders here is good.
                try:
                    sync_sip_child_orders(user=user, investor=investor_profile)
                    sync_pending_orders(user=user, investor=investor_profile)
                except Exception as e:
                    logger.error(f"Sync failed for investor {user.username}: {e}")

            except InvestorProfile.DoesNotExist:
                pass

        if investor_profile:
            valuation_data = calculate_portfolio_valuation(investor_profile)

            # Inject Redemption URL
            for holding in valuation_data['holdings']:
                holding['redemption_url'] = reverse('investments:redemption_create', args=[holding['id']])

            context['valuation'] = valuation_data
            context['grid_data_json'] = json.dumps(valuation_data['holdings'], default=str)

        return context

# --- User Management Views (The Permissions Layer) ---

# 1. RM Management (Admin Only)
class RMListView(LoginRequiredMixin, IsAdminMixin, ListView):
    model = RMProfile
    template_name = 'users/rm_list.html'
    context_object_name = 'rms'

    def get_queryset(self):
        return super().get_queryset().select_related('branch', 'user')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = []
        for rm in self.get_queryset():
            data.append({
                'id': rm.id,
                'name': rm.user.name if rm.user.name else rm.user.username,
                'email': rm.user.email,
                'employee_code': rm.employee_code,
                'branch': rm.branch.name if rm.branch else '-',
                'status': 'Active' if rm.user.is_active else 'Inactive',
                'action_url': reverse('users:rm_update', args=[rm.pk])
            })
        context['grid_data_json'] = json.dumps(data)
        return context

class RMCreateView(LoginRequiredMixin, IsAdminMixin, CreateView):
    model = User # Form handles User + Profile
    form_class = RMCreationForm
    template_name = 'users/rm_form.html'
    success_url = reverse_lazy('users:rm_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Create Relationship Manager"
        return context

class RMUpdateView(LoginRequiredMixin, IsAdminMixin, UpdateView):
    model = RMProfile
    form_class = RMChangeForm
    template_name = 'users/rm_form.html'
    success_url = reverse_lazy('users:rm_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Update Relationship Manager"
        context['is_update'] = True
        return context

# 2. Distributor Management (Admin & RM)
class DistributorListView(LoginRequiredMixin, IsAdminOrRMMixin, ListView):
    model = DistributorProfile
    template_name = 'users/distributor_list.html'
    context_object_name = 'distributors'

    def get_queryset(self):
        qs = super().get_queryset().select_related('user', 'rm', 'rm__user')
        user = self.request.user
        if user.user_type == User.Types.RM:
            # RM sees only their assigned distributors
            return qs.filter(rm__user=user)
        return qs # Admin sees all

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = []
        for dist in self.get_queryset():
            data.append({
                'id': dist.id,
                'name': dist.user.name if dist.user.name else dist.user.username,
                'arn': dist.arn_number,
                'mobile': dist.mobile,
                'rm_name': dist.rm.user.name if dist.rm and dist.rm.user.name else (dist.rm.user.username if dist.rm else ''),
                'status': 'Active' if dist.user.is_active else 'Inactive',
                'action_url': reverse('users:distributor_update', args=[dist.pk])
            })
        context['grid_data_json'] = json.dumps(data)
        return context

class DistributorCreateView(LoginRequiredMixin, IsAdminOrRMMixin, CreateView):
    form_class = DistributorCreationForm
    template_name = 'users/distributor_form.html'
    success_url = reverse_lazy('users:distributor_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['rm_user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Create Distributor"
        return context

class DistributorUpdateView(LoginRequiredMixin, IsAdminOrRMMixin, UpdateView):
    model = DistributorProfile
    form_class = DistributorChangeForm
    template_name = 'users/distributor_form.html'
    success_url = reverse_lazy('users:distributor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Update Distributor"
        context['is_update'] = True
        return context

# 3. Investor Management (Admin, RM, Distributor)
# Logic: Distributor sees own; RM sees investors of their distributors; Admin sees all.

class InvestorAccessMixin(UserPassesTestMixin):
    """
    Mixin to restrict access to Investor objects based on hierarchy.
    """
    def test_func(self):
        obj = self.get_object()
        user = self.request.user

        if user.user_type == User.Types.ADMIN:
            return True
        elif user.user_type == User.Types.INVESTOR:
            return obj.user == user
        elif user.user_type == User.Types.DISTRIBUTOR:
            return obj.distributor and obj.distributor.user == user
        elif user.user_type == User.Types.RM:
            # Direct RM or RM of Distributor
            is_direct_rm = obj.rm and obj.rm.user == user
            is_distributor_rm = obj.distributor and obj.distributor.rm and obj.distributor.rm.user == user
            return is_direct_rm or is_distributor_rm

        return False

class InvestorListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = InvestorProfile
    template_name = 'users/investor_list.html'
    context_object_name = 'investors'

    def test_func(self):
        # Investors cannot view the list of investors
        return self.request.user.user_type in [User.Types.ADMIN, User.Types.RM, User.Types.DISTRIBUTOR]

    def get_queryset(self):
        qs = super().get_queryset().select_related('user', 'distributor', 'distributor__user')
        user = self.request.user
        if user.user_type == User.Types.DISTRIBUTOR:
            return qs.filter(distributor__user=user)
        elif user.user_type == User.Types.RM:
            # RM sees investors where (distributor.rm == self) OR (rm == self [Direct])
            return qs.filter(models.Q(distributor__rm__user=user) | models.Q(rm__user=user))
        elif user.user_type == User.Types.ADMIN:
            return qs
        return qs.none() # Investors can't see list of investors

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = []
        for inv in self.get_queryset():
            data.append({
                'id': inv.id,
                'name': inv.user.name if inv.user.name else inv.user.username,
                'pan': inv.pan,
                'mobile': inv.mobile,
                'distributor_name': inv.distributor.user.name if inv.distributor and inv.distributor.user.name else (inv.distributor.user.username if inv.distributor else ''),
                'status': 'Active' if inv.user.is_active else 'Inactive',
                'detail_url': reverse('users:investor_detail', args=[inv.pk]),
                'action_url': reverse('users:investor_update', args=[inv.pk])
            })
        context['grid_data_json'] = json.dumps(data)
        return context

class InvestorCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = InvestorProfile
    form_class = InvestorProfileForm
    template_name = 'users/investor_onboarding.html'
    success_url = reverse_lazy('users:investor_list')

    def test_func(self):
        # Investors cannot create other investors
        return self.request.user.user_type in [User.Types.ADMIN, User.Types.RM, User.Types.DISTRIBUTOR]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Onboard Investor"
        if self.request.POST:
            context['bank_accounts'] = BankAccountFormSet(self.request.POST)
            context['nominees'] = NomineeFormSet(self.request.POST)
        else:
            context['bank_accounts'] = BankAccountFormSet()
            context['nominees'] = NomineeFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        bank_accounts = context['bank_accounts']
        nominees = context['nominees']

        try:
            with transaction.atomic():
                # 1. Create User
                pan = form.cleaned_data['pan']
                fname = form.cleaned_data.get('firstname', '').strip()
                mname = form.cleaned_data.get('middlename', '').strip()
                lname = form.cleaned_data.get('lastname', '').strip()
                full_name = f"{fname} {mname} {lname}".replace('  ', ' ').strip()
                email = form.cleaned_data['email']

                user = User.objects.create_user(
                    username=pan,
                    email=email,
                    password=pan,
                    name=full_name,
                    user_type=User.Types.INVESTOR
                )

                # 2. Save Investor Profile
                self.object = form.save(commit=False)
                self.object.user = user

                # --- Hierarchy Logic ---
                if self.request.user.user_type == User.Types.DISTRIBUTOR:
                    # Distributor creates: Forced hierarchy
                    dist = self.request.user.distributor_profile
                    self.object.distributor = dist
                    self.object.rm = dist.rm
                    if dist.rm:
                        self.object.branch = dist.rm.branch

                elif self.request.user.user_type == User.Types.RM:
                    # RM creates:
                    # If they picked a distributor (handled by form), use it.
                    # If distributor is set, sync RM/Branch.
                    # If distributor is None (Direct), set RM to self, Branch to self.

                    selected_distributor = form.cleaned_data.get('distributor')

                    if selected_distributor:
                        # Consistency check: The selected distributor must belong to this RM (filtered in form, but double check)
                        if selected_distributor.rm and selected_distributor.rm.user != self.request.user:
                             # This shouldn't happen if form queryset is correct, but safe fallback
                             # Force RM to be the distributor's RM
                             self.object.rm = selected_distributor.rm
                        else:
                             self.object.rm = self.request.user.rm_profile

                        if self.object.rm:
                             self.object.branch = self.object.rm.branch
                    else:
                        # Direct Client
                        self.object.rm = self.request.user.rm_profile
                        self.object.branch = self.request.user.rm_profile.branch

                elif self.request.user.user_type == User.Types.ADMIN:
                    # Admin creates:
                    # Form data for Distributor/RM/Branch takes precedence.
                    # However, we should enforce consistency if Distributor is selected.
                    dist = form.cleaned_data.get('distributor')
                    if dist:
                        self.object.rm = dist.rm
                        if dist.rm:
                            self.object.branch = dist.rm.branch
                    # If no distributor, respect RM/Branch selected in form.
                    # If RM selected but no Branch, populate Branch.
                    if not dist and form.cleaned_data.get('rm') and not form.cleaned_data.get('branch'):
                         self.object.branch = form.cleaned_data.get('rm').branch

                self.object.kyc_status = True  # Mock KYC
                self.object.save()

                # 3. Save Formsets
                if bank_accounts.is_valid() and nominees.is_valid():
                    bank_accounts.instance = self.object
                    bank_accounts.save()
                    nominees.instance = self.object
                    nominees.save()
                else:
                    raise ValueError("Formsets invalid")

        except ValueError:
            return self.form_invalid(form)

        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': 'Investor Profile Created Successfully'})

        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            errors = dict(form.errors.items())
            # Add formset errors if any
            context = self.get_context_data()
            if 'bank_accounts' in context and not context['bank_accounts'].is_valid():
                errors['bank_accounts'] = context['bank_accounts'].errors
            if 'nominees' in context and not context['nominees'].is_valid():
                errors['nominees'] = context['nominees'].errors

            return JsonResponse({'status': 'error', 'errors': errors}, status=400)
        return super().form_invalid(form)

class InvestorUpdateView(LoginRequiredMixin, InvestorAccessMixin, UpdateView):
    model = InvestorProfile
    form_class = InvestorProfileForm
    template_name = 'users/investor_onboarding.html'
    success_url = reverse_lazy('users:investor_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Update Investor"
        if self.request.POST:
            context['bank_accounts'] = BankAccountFormSet(self.request.POST, instance=self.object)
            context['nominees'] = NomineeFormSet(self.request.POST, instance=self.object)
        else:
            context['bank_accounts'] = BankAccountFormSet(instance=self.object)
            context['nominees'] = NomineeFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        bank_accounts = context['bank_accounts']
        nominees = context['nominees']

        try:
            with transaction.atomic():
                # 1. Update User (Name/Email)
                fname = form.cleaned_data.get('firstname', '').strip()
                mname = form.cleaned_data.get('middlename', '').strip()
                lname = form.cleaned_data.get('lastname', '').strip()
                email = form.cleaned_data.get('email')

                # Construct full name and update User
                user = self.object.user
                full_name = f"{fname} {mname} {lname}".replace('  ', ' ').strip()
                if full_name:
                    user.name = full_name
                if email:
                    user.email = email
                user.save()

                # 2. Save Investor Profile
                self.object = form.save(commit=False)

                # --- Hierarchy Update Logic ---
                # Enforce consistency if Distributor changes
                # Note: We trust the form's logic for filtering choices, but backend enforcement is safer.

                new_distributor = form.cleaned_data.get('distributor')
                # If user has permission to change distributor (Admin or RM)
                if self.request.user.user_type in [User.Types.ADMIN, User.Types.RM]:
                     if new_distributor:
                          # If a distributor is set, it dictates the chain.
                          self.object.rm = new_distributor.rm
                          if new_distributor.rm:
                               self.object.branch = new_distributor.rm.branch
                          else:
                               # If Distributor has no RM (Root?), maybe leave existing RM or clear?
                               # Assuming Distributor always has RM or Root is special case.
                               # If Root (Direct to Company via Dist), RM might be null?
                               # For now, let's assume we sync.
                               pass
                     else:
                          # If Distributor is cleared (Direct)
                          # If Admin, they could have manually set RM/Branch.
                          # If RM, they are likely setting it to Direct under THEMSELVES.
                          if self.request.user.user_type == User.Types.RM:
                               self.object.rm = self.request.user.rm_profile
                               self.object.branch = self.request.user.rm_profile.branch

                self.object.save()

                # 3. Save Formsets
                if bank_accounts.is_valid() and nominees.is_valid():
                    bank_accounts.save()
                    nominees.save()
                else:
                    # If formsets are invalid, render the form again with errors
                    raise ValueError("Formsets invalid")

        except ValueError:
            return self.form_invalid(form)

        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': 'Investor Profile Updated Successfully'})

        # Manually return response instead of calling super().form_valid() which would save again
        return redirect(self.success_url)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            errors = dict(form.errors.items())
            # Add formset errors
            context = self.get_context_data()
            if 'bank_accounts' in context and not context['bank_accounts'].is_valid():
                errors['bank_accounts'] = context['bank_accounts'].errors
            if 'nominees' in context and not context['nominees'].is_valid():
                errors['nominees'] = context['nominees'].errors

            return JsonResponse({'status': 'error', 'errors': errors}, status=400)
        return super().form_invalid(form)

class InvestorDetailView(LoginRequiredMixin, InvestorAccessMixin, DetailView):
    model = InvestorProfile
    template_name = 'users/investor_detail.html'
    context_object_name = 'investor'

    def get_context_data(self, **kwargs):
        # Sync Mandates status here as user is viewing the details
        # Pass self.object (investor) to sync_pending_mandates to avoid syncing ALL mandates if Admin
        try:
            sync_pending_mandates(user=self.request.user, investor=self.object)
            # Also sync pending orders for this specific investor
            sync_pending_orders(user=self.request.user, investor=self.object)
        except Exception as e:
            logger.error(f"Sync failed in InvestorDetailView: {e}")

        context = super().get_context_data(**kwargs)
        context['bank_accounts'] = self.object.bank_accounts.all()
        context['nominees'] = self.object.nominees.all()
        context['documents'] = self.object.documents.all()
        context['document_form'] = DocumentForm()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if request.user.user_type not in [User.Types.RM, User.Types.DISTRIBUTOR, User.Types.ADMIN]:
             messages.error(request, "Permission denied.")
             return redirect('users:investor_detail', pk=self.object.pk)

        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.investor = self.object
            document.save()
            messages.success(request, "Document uploaded successfully.")
            return redirect('users:investor_detail', pk=self.object.pk)
        else:
             messages.error(request, "Error uploading document.")
             context = self.get_context_data()
             context['document_form'] = form
             return self.render_to_response(context)

class PushToBSEView(LoginRequiredMixin, View):
    def post(self, request, pk):
        investor = get_object_or_404(InvestorProfile, pk=pk)

        if request.user.user_type not in [User.Types.RM, User.Types.DISTRIBUTOR, User.Types.ADMIN]:
             messages.error(request, "Permission denied.")
             return redirect('users:investor_detail', pk=pk)

        # 1. Strict Pre-Validation
        validation_errors = validate_investor_for_bse(investor)
        if validation_errors:
            for err in validation_errors:
                messages.error(request, err)
            return redirect('users:investor_detail', pk=pk)

        # 2. Map Data
        try:
            param_string = map_investor_to_bse_param_string(investor)
        except Exception as e:
            messages.error(request, f"Data Mapping Error: {str(e)}")
            return redirect('users:investor_detail', pk=pk)

        # 3. Call API
        client = BSEStarMFClient()

        # Determine Registration Type: NEW or MOD
        regn_type = "MOD" if investor.ucc_code else "NEW"

        try:
            response = client.register_client({'Param': param_string}, regn_type=regn_type)
            if response['status'] == 'success':
                # If success, the UCC we sent (which defaults to PAN) is now valid.
                if not investor.ucc_code:
                    investor.ucc_code = investor.pan
                    investor.save()

                # Check for remarks to update nominee status
                remarks = response.get('remarks', '').upper()
                investor.bse_remarks = remarks
                investor.last_verified_at = timezone.now()

                if "AUTHENTICATED" in remarks or "ACTIVE" in remarks:
                    investor.nominee_auth_status = InvestorProfile.AUTH_AUTHENTICATED
                elif "PENDING" in remarks:
                    investor.nominee_auth_status = InvestorProfile.AUTH_PENDING

                investor.save()

                messages.success(request, f"BSE {regn_type} Registration Successful: {response.get('remarks')}")

                # 4. Trigger FATCA Upload automatically after successful registration
                fatca_response = client.fatca_upload(investor)
                if fatca_response['status'] == 'success':
                    messages.success(request, f"FATCA Upload Successful: {fatca_response.get('remarks')}")
                else:
                    messages.warning(request, f"FATCA Upload Warning: {fatca_response.get('remarks')}")

            else:
                # Handle "MODIFICATION NOT FOUND" as a non-error
                remarks = response.get('remarks', '')
                if "FAILED : MODIFICATION NOT FOUND" in remarks.upper():
                    messages.info(request, "BSE Record is already up to date. No changes were necessary.")
                else:
                    messages.error(request, f"BSE Error: {remarks}")
        except Exception as e:
             messages.error(request, f"API Call Failed: {str(e)}")

        return redirect('users:investor_detail', pk=pk)


class DistributorMappingView(LoginRequiredMixin, IsAdminOrRMMixin, TemplateView):
    template_name = 'users/distributor_mapping.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get selected investor IDs from query string
        investor_ids = self.request.GET.get('ids', '')
        context['investor_ids'] = investor_ids
        context['selected_count'] = len([x for x in investor_ids.split(',') if x.strip()]) if investor_ids else 0

        # Fetch Distributors based on Role
        if user.user_type == User.Types.ADMIN:
            context['distributors'] = DistributorProfile.objects.select_related('user').all()
        elif user.user_type == User.Types.RM:
            context['distributors'] = DistributorProfile.objects.select_related('user').filter(rm__user=user)

        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        if action == 'assign_selected':
            return self.handle_manual_assignment(request)
        elif action == 'upload_csv':
            return self.handle_csv_upload(request)

        messages.error(request, "Invalid Action")
        return redirect('users:distributor_mapping')

    def handle_manual_assignment(self, request):
        investor_ids_str = request.POST.get('investor_ids', '')
        distributor_id = request.POST.get('distributor_id')

        if not investor_ids_str:
            messages.error(request, "No investors selected.")
            return redirect('users:distributor_mapping')

        investor_ids = [int(id) for id in investor_ids_str.split(',') if id.isdigit()]

        # Validate Distributor Access
        distributor = None
        if distributor_id:
            try:
                qs = DistributorProfile.objects.all()
                if request.user.user_type == User.Types.RM:
                    qs = qs.filter(rm__user=request.user)
                distributor = qs.get(pk=distributor_id)
            except DistributorProfile.DoesNotExist:
                messages.error(request, "Invalid Distributor Selected.")
                return redirect('users:distributor_mapping')

        # Scope Validation for Investors
        # RMs can only map investors they already have access to
        investors = InvestorProfile.objects.filter(id__in=investor_ids)
        if request.user.user_type == User.Types.RM:
            # RM can see investors if (distributor.rm == self) OR (rm == self)
            investors = investors.filter(
                models.Q(distributor__rm__user=request.user) | models.Q(rm__user=request.user)
            )

        updated_count = 0
        with transaction.atomic():
            for investor in investors:
                investor.distributor = distributor

                # Update Hierarchy
                if distributor:
                    investor.rm = distributor.rm
                    if distributor.rm:
                        investor.branch = distributor.rm.branch
                else:
                    # If Unassigning (Direct)
                    # If RM is performing this, set RM to self (Direct under RM)
                    if request.user.user_type == User.Types.RM:
                         investor.rm = request.user.rm_profile
                         if investor.rm:
                            investor.branch = investor.rm.branch
                    # If Admin unassigns, we leave RM/Branch as is (orphaned from dist context but valid)
                    # OR we could clear them? Usually Direct clients have an RM.
                    pass

                investor.save()
                updated_count += 1

        messages.success(request, f"Successfully mapped {updated_count} investors.")
        return redirect('users:investor_list')

    def handle_csv_upload(self, request):
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, "Please upload a CSV file.")
            return redirect('users:distributor_mapping')

        if not csv_file.name.endswith('.csv'):
             messages.error(request, "Invalid file format. Please upload a CSV.")
             return redirect('users:distributor_mapping')

        try:
            decoded_file = csv_file.read().decode('utf-8-sig').splitlines()
            reader = csv.DictReader(decoded_file)

            # Normalize headers
            if reader.fieldnames:
                reader.fieldnames = [name.lower().strip() for name in reader.fieldnames]

            if 'investor_pan' not in reader.fieldnames or 'distributor_arn' not in reader.fieldnames:
                 messages.error(request, "CSV must contain 'investor_pan' and 'distributor_arn' columns.")
                 return redirect('users:distributor_mapping')

            success_count = 0
            errors = []

            with transaction.atomic():
                for row_idx, row in enumerate(reader, start=1):
                    pan = row.get('investor_pan', '').strip()
                    arn = row.get('distributor_arn', '').strip()

                    if not pan: continue

                    # 1. Find Investor
                    try:
                        investor = InvestorProfile.objects.get(pan__iexact=pan)
                    except InvestorProfile.DoesNotExist:
                        errors.append(f"Row {row_idx}: Investor PAN {pan} not found.")
                        continue

                    # Scope Check for Investor (RM)
                    if request.user.user_type == User.Types.RM:
                        # Check if RM has access to this investor
                        has_access = False
                        if investor.rm and investor.rm.user == request.user:
                            has_access = True
                        elif investor.distributor and investor.distributor.rm and investor.distributor.rm.user == request.user:
                            has_access = True

                        if not has_access:
                           errors.append(f"Row {row_idx}: Permission denied for PAN {pan}.")
                           continue

                    # 2. Find Distributor
                    distributor = None
                    if arn:
                        try:
                            qs = DistributorProfile.objects.all()
                            if request.user.user_type == User.Types.RM:
                                qs = qs.filter(rm__user=request.user)
                            distributor = qs.get(arn_number__iexact=arn)
                        except DistributorProfile.DoesNotExist:
                            errors.append(f"Row {row_idx}: Distributor ARN {arn} not found (or access denied).")
                            continue

                    # 3. Apply Mapping
                    investor.distributor = distributor
                    if distributor:
                        investor.rm = distributor.rm
                        if distributor.rm:
                            investor.branch = distributor.rm.branch
                    else:
                        # Unassign Logic
                        if request.user.user_type == User.Types.RM:
                             investor.rm = request.user.rm_profile
                             if investor.rm:
                                investor.branch = investor.rm.branch

                    investor.save()
                    success_count += 1

            if errors:
                for err in errors[:5]: # Show first 5 errors
                    messages.warning(request, err)
                if len(errors) > 5:
                    messages.warning(request, f"...and {len(errors)-5} more errors.")

            if success_count > 0:
                messages.success(request, f"Successfully processed {success_count} rows.")

        except Exception as e:
            messages.error(request, f"Error processing CSV: {str(e)}")

        return redirect('users:distributor_mapping')

class FATCAUploadView(LoginRequiredMixin, View):
    """
    Manually triggers FATCA Upload for an investor.
    """
    def post(self, request, pk):
        investor = get_object_or_404(InvestorProfile, pk=pk)

        if request.user.user_type not in [User.Types.RM, User.Types.DISTRIBUTOR, User.Types.ADMIN]:
             messages.error(request, "Permission denied.")
             return redirect('users:investor_detail', pk=pk)

        # Ensure we have a UCC Code before triggering FATCA
        if not investor.ucc_code:
            messages.error(request, "Investor must have a UCC Code (Registered on BSE) to upload FATCA details.")
            return redirect('users:investor_detail', pk=pk)

        client = BSEStarMFClient()
        try:
            response = client.fatca_upload(investor)
            if response['status'] == 'success':
                messages.success(request, f"FATCA Upload Successful: {response.get('remarks')}")
            else:
                messages.error(request, f"FATCA Upload Failed: {response.get('remarks')}")
        except Exception as e:
            messages.error(request, f"FATCA API Error: {str(e)}")

        return redirect('users:investor_detail', pk=pk)

class TriggerNomineeAuthView(LoginRequiredMixin, View):
    """
    Triggers Nominee Authentication via a BSE Modification (MOD) request.
    It also acts as a Status Checker by parsing the response remarks.
    """
    def post(self, request, pk):
        investor = get_object_or_404(InvestorProfile, pk=pk)

        if request.user.user_type not in [User.Types.RM, User.Types.DISTRIBUTOR, User.Types.ADMIN]:
             messages.error(request, "Permission denied.")
             return redirect('users:investor_detail', pk=pk)

        # Ensure we have a UCC Code before triggering modification
        if not investor.ucc_code:
            messages.error(request, "Investor must have a UCC Code (Registered on BSE) to trigger authentication.")
            return redirect('users:investor_detail', pk=pk)

        # 1. Validation
        validation_errors = validate_investor_for_bse(investor)
        if validation_errors:
            for err in validation_errors:
                messages.error(request, err)
            return redirect('users:investor_detail', pk=pk)

        # 2. Map Data
        try:
            param_string = map_investor_to_bse_param_string(investor)
        except Exception as e:
            messages.error(request, f"Data Mapping Error: {str(e)}")
            return redirect('users:investor_detail', pk=pk)

        # 3. Call API (MOD Request)
        client = BSEStarMFClient()
        try:
            # We use MOD to trigger the auth email/sms or check status
            response = client.register_client({'Param': param_string}, regn_type="MOD")

            investor.bse_remarks = response.get('remarks', '')
            investor.last_verified_at = timezone.now()

            if response['status'] == 'success':
                remarks = response.get('remarks', '').upper()

                # Intelligent Status Parsing
                if "AUTHENTICATED" in remarks or "ACTIVE" in remarks:
                    investor.nominee_auth_status = InvestorProfile.AUTH_AUTHENTICATED
                    msg_type = messages.success
                elif "PENDING" in remarks:
                    investor.nominee_auth_status = InvestorProfile.AUTH_PENDING
                    msg_type = messages.warning
                else:
                    # Fallback if status is unclear but request succeeded
                    # We might want to keep it as is or set to N if it was P
                    # But safest is to trust the 'remarks' text if it mentions auth
                    msg_type = messages.info

                investor.save()
                msg_type(request, f"Trigger/Check Successful: {response.get('remarks')}")

            else:
                # If error, it might be "Nominee Auth Pending" which is actually valuable info
                remarks = response.get('remarks', '').upper()
                if "PENDING" in remarks and "NOMINEE" in remarks:
                    investor.nominee_auth_status = InvestorProfile.AUTH_PENDING
                    investor.save()
                    messages.warning(request, f"BSE Response: {response.get('remarks')}")
                else:
                    messages.error(request, f"BSE Error: {response.get('remarks')}")

        except Exception as e:
            messages.error(request, f"API Call Failed: {str(e)}")

        return redirect('users:investor_detail', pk=pk)

class OptOutNomineeView(LoginRequiredMixin, View):
    def post(self, request, pk):
        investor = get_object_or_404(InvestorProfile, pk=pk)

        # Permission Check
        if request.user.user_type not in [User.Types.RM, User.Types.ADMIN]:
             messages.error(request, "Permission denied.")
             return redirect('users:investor_detail', pk=pk)

        # Update Flag in memory (Do not save yet)
        investor.nomination_opt = 'N'

        # Ensure we have a UCC Code
        if not investor.ucc_code:
            # We can't update BSE without UCC.
            # Do we still save locally? The requirement is to "update the ucc".
            # If we update locally but not BSE, data is inconsistent.
            # However, if UCC is missing, maybe they aren't on BSE yet?
            # But the button is likely only visible if UCC is present (per template logic check I should add).
            # If they click it, we should probably fail gracefully.
            messages.error(request, "Cannot update BSE: UCC Code is missing.")
            return redirect('users:investor_detail', pk=pk)

        # Validate (Optional but good practice)
        validation_errors = validate_investor_for_bse(investor)
        if validation_errors:
             for err in validation_errors:
                messages.error(request, f"BSE Validation Warning: {err}")
             # Should we abort? If validation fails, BSE API will likely fail anyway.
             # We proceed to try.

        try:
            client = BSEStarMFClient()
            # Use Bulk Update API for targeted flag update (avoids full profile validation issues)
            response = client.bulk_update_nominee_flags([investor])

            if response['status'] == 'success':
                 # Success! Now update DB.
                 investor.nominee_auth_status = InvestorProfile.AUTH_NOT_AVAILABLE
                 investor.bse_remarks = response.get('remarks', '')
                 investor.last_verified_at = timezone.now()
                 investor.save() # Saves nomination_opt='N'
                 messages.success(request, f"Nomination Opt-Out successful on BSE: {response.get('remarks')}")
            else:
                 # Failure! Do not save changes.
                 messages.error(request, f"BSE Update Failed: {response.get('remarks')}")
        except Exception as e:
            messages.error(request, f"API Error: {str(e)}")

        return redirect('users:investor_detail', pk=pk)

class ToggleKYCView(LoginRequiredMixin, View):
    def post(self, request, pk):
        investor = get_object_or_404(InvestorProfile, pk=pk)

        if request.user.user_type not in [User.Types.RM, User.Types.DISTRIBUTOR, User.Types.ADMIN]:
             messages.error(request, "Permission denied.")
             return redirect('users:investor_detail', pk=pk)

        investor.kyc_status = not investor.kyc_status
        investor.save()

        status_msg = "Verified" if investor.kyc_status else "Revoked"
        messages.success(request, f"KYC Status {status_msg}.")

        return redirect('users:investor_detail', pk=pk)

class InvestorUploadView(LoginRequiredMixin, IsAdminMixin, FormView):
    template_name = 'users/upload_investor.html'
    form_class = InvestorUploadForm
    success_url = reverse_lazy('users:investor_list')

    def form_valid(self, form):
        file_obj = self.request.FILES['file']
        count, errors = import_investors_from_file(file_obj)

        if errors:
            messages.warning(self.request, f"Processed {count} investors with errors: {errors[:5]}...")
        else:
            messages.success(self.request, f"Successfully imported {count} investors.")

        return super().form_valid(form)

class DistributorUploadView(LoginRequiredMixin, IsAdminMixin, FormView):
    template_name = 'users/upload_distributor.html'
    form_class = DistributorUploadForm
    success_url = reverse_lazy('users:distributor_list')

    def form_valid(self, form):
        file_obj = self.request.FILES['file']
        count, errors = import_distributors_from_file(file_obj)

        if errors:
             messages.warning(self.request, f"Processed {count} distributors with errors: {errors[:5]}...")
        else:
             messages.success(self.request, f"Successfully imported {count} distributors.")

        return super().form_valid(form)

class DownloadInvestorSampleView(LoginRequiredMixin, IsAdminOrRMMixin, View):
    def get(self, request, *args, **kwargs):
        excel_file = create_excel_sample_file(INVESTOR_HEADERS, INVESTOR_CHOICES)
        response = HttpResponse(
            excel_file.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="investor_import_sample.xlsx"'
        return response

class DownloadDistributorSampleView(LoginRequiredMixin, IsAdminMixin, View):
    def get(self, request, *args, **kwargs):
        excel_file = create_excel_sample_file(DISTRIBUTOR_HEADERS, DISTRIBUTOR_CHOICES)
        response = HttpResponse(
            excel_file.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="distributor_import_sample.xlsx"'
        return response

class RMUploadView(LoginRequiredMixin, IsAdminMixin, FormView):
    template_name = 'users/upload_rm.html'
    form_class = RMUploadForm
    success_url = reverse_lazy('users:rm_list')

    def form_valid(self, form):
        file_obj = self.request.FILES['file']
        count, errors = import_rms_from_file(file_obj)

        if errors:
             messages.warning(self.request, f"Processed {count} RMs with errors: {errors[:5]}...")
        else:
             messages.success(self.request, f"Successfully imported {count} RMs.")

        return super().form_valid(form)

class DownloadRMSampleView(LoginRequiredMixin, IsAdminMixin, View):
    def get(self, request, *args, **kwargs):
        excel_file = create_excel_sample_file(RM_HEADERS, RM_CHOICES)
        response = HttpResponse(
            excel_file.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="rm_import_sample.xlsx"'
        return response

# --- Profile & Settings Views ---

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.user_type == User.Types.INVESTOR:
            try:
                investor = user.investor_profile
                context['investor'] = investor
                context['bank_accounts'] = investor.bank_accounts.all()
                context['nominees'] = investor.nominees.all()
                context['documents'] = investor.documents.all()
            except InvestorProfile.DoesNotExist:
                pass
        elif user.user_type == User.Types.RM:
            try:
                context['rm'] = user.rm_profile
            except RMProfile.DoesNotExist:
                pass
        elif user.user_type == User.Types.DISTRIBUTOR:
            try:
                context['distributor'] = user.distributor_profile
            except DistributorProfile.DoesNotExist:
                pass

        return context

class ProfileEditView(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile_edit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Initialize forms
        if 'user_form' not in context:
            context['user_form'] = UserProfileForm(instance=user)

        # Profile specific form
        if user.user_type == User.Types.RM and hasattr(user, 'rm_profile'):
            if 'profile_form' not in context:
                context['profile_form'] = RMProfileUpdateForm(instance=user.rm_profile)
        elif user.user_type == User.Types.DISTRIBUTOR and hasattr(user, 'distributor_profile'):
            if 'profile_form' not in context:
                context['profile_form'] = DistributorProfileUpdateForm(instance=user.distributor_profile)

        return context

    def post(self, request, *args, **kwargs):
        user = request.user
        user_form = UserProfileForm(request.POST, instance=user)
        profile_form = None

        valid_profile = True

        if user.user_type == User.Types.RM and hasattr(user, 'rm_profile'):
            profile_form = RMProfileUpdateForm(request.POST, instance=user.rm_profile)
        elif user.user_type == User.Types.DISTRIBUTOR and hasattr(user, 'distributor_profile'):
            profile_form = DistributorProfileUpdateForm(request.POST, instance=user.distributor_profile)

        valid_user = user_form.is_valid()
        if profile_form:
            valid_profile = profile_form.is_valid()

        if valid_user and valid_profile:
            user_form.save()
            if profile_form:
                profile_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('users:profile')
        else:
            messages.error(request, "Please correct the errors below.")
            return self.render_to_response(self.get_context_data(user_form=user_form, profile_form=profile_form))

from django.contrib.auth.views import (
    PasswordChangeView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView
)

class UserPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'users/password_change.html'
    success_url = reverse_lazy('users:profile')

    def form_valid(self, form):
        messages.success(self.request, "Password changed successfully.")
        return super().form_valid(form)

class UserPasswordResetView(PasswordResetView):
    template_name = 'users/password_reset_form.html'
    email_template_name = 'users/password_reset_email.html'
    success_url = reverse_lazy('users:password_reset_done')

class UserPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'users/password_reset_done.html'

class UserPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('users:password_reset_complete')

class UserPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'users/password_reset_complete.html'
