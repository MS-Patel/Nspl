from django import forms
from .models import Order, Folio
from apps.users.models import InvestorProfile
from apps.products.models import Scheme
from django.core.exceptions import ValidationError

class OrderCreationForm(forms.ModelForm):
    # Field to select an existing folio or leave blank for new
    folio_selection = forms.ModelChoiceField(
        queryset=Folio.objects.none(),
        required=False,
        label="Existing Folio",
        empty_label="Create New Folio"
    )

    class Meta:
        model = Order
        fields = ['investor', 'scheme', 'amount', 'folio_selection', 'payment_mode']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        user = self.request.user if self.request else None

        super().__init__(*args, **kwargs)

        # 1. Filter Investors based on User Role
        if user:
            if user.user_type == user.Types.DISTRIBUTOR:
                self.fields['investor'].queryset = InvestorProfile.objects.filter(distributor__user=user)
            elif user.user_type == user.Types.RM:
                # RM can see investors of their distributors
                self.fields['investor'].queryset = InvestorProfile.objects.filter(distributor__rm__user=user)
            elif user.user_type == user.Types.ADMIN:
                self.fields['investor'].queryset = InvestorProfile.objects.all()
            else:
                self.fields['investor'].queryset = InvestorProfile.objects.none()

        # 2. Dynamic Folio Filtering (This usually requires HTMX or JS, but we handle initial load)
        # If 'investor' or 'scheme' is already selected (e.g. bound form or initial), filter folios
        investor_id = self.data.get('investor') or self.initial.get('investor')
        scheme_id = self.data.get('scheme') or self.initial.get('scheme')

        if investor_id and scheme_id:
            try:
                scheme = Scheme.objects.get(pk=scheme_id)
                self.fields['folio_selection'].queryset = Folio.objects.filter(
                    investor_id=investor_id,
                    amc=scheme.amc
                )
            except (ValueError, Scheme.DoesNotExist):
                pass
        elif investor_id:
             self.fields['folio_selection'].queryset = Folio.objects.filter(investor_id=investor_id)

        # Style widgets (if not using render_field in template, but good practice to add classes here too)
        self.fields['investor'].widget.attrs.update({'class': 'form-select'})
        self.fields['scheme'].widget.attrs.update({'class': 'form-select'})
        self.fields['amount'].widget.attrs.update({'class': 'form-input'})
        self.fields['folio_selection'].widget.attrs.update({'class': 'form-select'})
        self.fields['payment_mode'].widget.attrs.update({'class': 'form-select'})

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        scheme = cleaned_data.get('scheme')

        if amount and scheme:
            if amount < scheme.min_purchase_amount:
                self.add_error('amount', f"Minimum purchase amount is {scheme.min_purchase_amount}")

        return cleaned_data

    def save(self, commit=True):
        order = super().save(commit=False)

        # Handle Folio Logic
        folio_selection = self.cleaned_data.get('folio_selection')
        if folio_selection:
            order.folio = folio_selection
            order.is_new_folio = False
        else:
            order.folio = None
            order.is_new_folio = True

        # Set Distributor
        if order.investor and order.investor.distributor:
            order.distributor = order.investor.distributor

        if commit:
            order.save()
        return order
