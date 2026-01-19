from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, CreateView, DetailView
from django.contrib.auth import get_user_model
from django.db import transaction
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.views import View
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import RMProfile, DistributorProfile, InvestorProfile, BankAccount, Nominee, Document
from .forms import RMCreationForm, DistributorCreationForm, InvestorCreationForm, InvestorProfileForm, BankAccountFormSet, NomineeFormSet, DocumentForm
from .services import validate_investor_for_bse
from apps.integration.bse_client import BSEStarMFClient
from apps.integration.utils import map_investor_to_bse_param_string
from apps.reconciliation.utils.valuation import calculate_portfolio_valuation
import json

User = get_user_model()

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Determine the Investor Profile
        investor_profile = None
        if user.user_type == User.Types.INVESTOR:
            # Handle potential DoesNotExist if profile creation failed (though it shouldn't)
            try:
                investor_profile = user.investor_profile
            except InvestorProfile.DoesNotExist:
                pass

        if investor_profile:
            valuation_data = calculate_portfolio_valuation(investor_profile)
            context['valuation'] = valuation_data
            context['grid_data_json'] = json.dumps(valuation_data['holdings'], default=str)

        return context

# --- User Management Views (The Permissions Layer) ---

# 1. RM Management (Admin Only)
class RMListView(LoginRequiredMixin, IsAdminMixin, ListView):
    model = RMProfile
    template_name = 'users/rm_list.html'
    context_object_name = 'rms'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = []
        for rm in self.get_queryset():
            data.append({
                'id': rm.id,
                'name': rm.user.name if rm.user.name else rm.user.username,
                'email': rm.user.email,
                'employee_code': rm.employee_code,
                'status': 'Active' if rm.user.is_active else 'Inactive',
                'action_url': '#' # Placeholder for edit/detail view
            })
        context['grid_data_json'] = json.dumps(data)
        return context

class RMCreateView(LoginRequiredMixin, IsAdminMixin, CreateView):
    model = User # Form handles User + Profile
    form_class = RMCreationForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:rm_list')

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
                'action_url': '#' # Placeholder
            })
        context['grid_data_json'] = json.dumps(data)
        return context

class DistributorCreateView(LoginRequiredMixin, IsAdminOrRMMixin, CreateView):
    form_class = DistributorCreationForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:distributor_list')

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

from django.views.generic import UpdateView

class InvestorCreateView(LoginRequiredMixin, CreateView):
    model = InvestorProfile
    form_class = InvestorProfileForm
    template_name = 'users/investor_onboarding.html'
    success_url = reverse_lazy('users:investor_list')

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

        with transaction.atomic():
            # 1. Create User
            pan = form.cleaned_data['pan']
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']

            if User.objects.filter(username=pan).exists():
                messages.error(self.request, f"User with PAN {pan} already exists.")
                return self.form_invalid(form)

            user = User.objects.create_user(
                username=pan,
                email=email,
                password=pan,
                name=name,
                user_type=User.Types.INVESTOR
            )

            # 2. Save Investor Profile
            self.object = form.save(commit=False)
            self.object.user = user

            if self.request.user.user_type == User.Types.DISTRIBUTOR:
                self.object.distributor = self.request.user.distributor_profile

            self.object.kyc_status = True  # Mock KYC
            self.object.save()

            # 3. Save Formsets
            if bank_accounts.is_valid() and nominees.is_valid():
                bank_accounts.instance = self.object
                bank_accounts.save()
                nominees.instance = self.object
                nominees.save()
            else:
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

class InvestorUpdateView(LoginRequiredMixin, UpdateView):
    model = InvestorProfile
    form_class = InvestorProfileForm
    template_name = 'users/investor_onboarding.html'
    success_url = reverse_lazy('users:investor_list')

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

        with transaction.atomic():
            # 1. Update User (Name/Email)
            name = form.cleaned_data.get('name')
            email = form.cleaned_data.get('email')
            if name or email:
                user = self.object.user
                if name: user.name = name
                if email: user.email = email
                user.save()

            # 2. Save Investor Profile
            self.object = form.save()

            # 3. Save Formsets
            if bank_accounts.is_valid() and nominees.is_valid():
                bank_accounts.save()
                nominees.save()
            else:
                # If formsets are invalid, render the form again with errors
                return self.form_invalid(form)

        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': 'Investor Profile Updated Successfully'})

        return super().form_valid(form)

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

class InvestorDetailView(LoginRequiredMixin, DetailView):
    model = InvestorProfile
    template_name = 'users/investor_detail.html'
    context_object_name = 'investor'

    def get_context_data(self, **kwargs):
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
            else:
                messages.error(request, f"BSE Error: {response.get('remarks')}")
        except Exception as e:
             messages.error(request, f"API Call Failed: {str(e)}")

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
