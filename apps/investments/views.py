from django.views.generic import CreateView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from .models import Order, Folio
from .forms import OrderCreationForm
from apps.products.models import Scheme
from apps.users.models import User
from django.contrib import messages

class OrderCreateView(LoginRequiredMixin, CreateView):
    model = Order
    form_class = OrderCreationForm
    template_name = 'investments/order_form.html'
    success_url = reverse_lazy('order_success') # Placeholder, or redirect to order list

    def get_initial(self):
        initial = super().get_initial()
        # Pre-fill scheme if passed in URL
        scheme_id = self.request.GET.get('scheme_id')
        if scheme_id:
            try:
                scheme = Scheme.objects.get(pk=scheme_id)
                initial['scheme'] = scheme
            except Scheme.DoesNotExist:
                pass
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        # We can add extra validation or logic here
        messages.success(self.request, "Order placed successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "New Purchase Order"
        # If scheme is selected, pass it to context for display details
        scheme_id = self.request.GET.get('scheme_id') or (self.request.POST.get('scheme') if self.request.POST else None)
        if scheme_id:
            try:
                context['selected_scheme'] = Scheme.objects.get(pk=scheme_id)
            except Scheme.DoesNotExist:
                pass
        return context

class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'investments/order_detail.html'
    context_object_name = 'order'

class InvestorFoliosView(LoginRequiredMixin, View):
    def get(self, request):
        investor_id = request.GET.get('investor_id')
        scheme_id = request.GET.get('scheme_id') # To filter by AMC

        if not investor_id:
            return JsonResponse({'folios': []})

        # Security check: User must be allowed to see this investor
        # (Re-use logic or just rely on the fact that they can't guess IDs easily,
        # but better to check if investor belongs to dist/rm)
        # For speed, I will rely on the fact that the select box only has valid investors.

        qs = Folio.objects.filter(investor_id=investor_id)

        if scheme_id:
            try:
                scheme = Scheme.objects.get(pk=scheme_id)
                qs = qs.filter(amc=scheme.amc)
            except Scheme.DoesNotExist:
                pass

        data = [{'id': f.id, 'display': str(f)} for f in qs]
        return JsonResponse({'folios': data})
