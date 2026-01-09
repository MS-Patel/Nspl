from django import forms
from .models import Order, Folio, Mandate
from apps.users.models import InvestorProfile
from apps.products.models import Scheme
from django.core.exceptions import ValidationError

class OrderForm(forms.ModelForm):
    # Field to select an existing folio or leave blank for new
    folio_selection = forms.ModelChoiceField(
        queryset=Folio.objects.none(),
        required=False,
        label="Existing Folio",
        empty_label="Create New Folio"
    )

    class Meta:
        model = Order
        fields = ['investor', 'scheme', 'amount', 'folio_selection', 'payment_mode', 'transaction_type', 'mandate']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None) # Pass user explicitly
        super().__init__(*args, **kwargs)

        # 1. Filter Investors based on User Role
        if self.user:
            if self.user.user_type == 'DISTRIBUTOR':
                self.fields['investor'].queryset = InvestorProfile.objects.filter(distributor__user=self.user)
            elif self.user.user_type == 'RM':
                self.fields['investor'].queryset = InvestorProfile.objects.filter(distributor__rm__user=self.user)
            elif self.user.user_type == 'ADMIN':
                self.fields['investor'].queryset = InvestorProfile.objects.all()
            elif self.user.user_type == 'INVESTOR':
                # For Investor, we might hide the field or single option
                self.fields['investor'].queryset = InvestorProfile.objects.filter(user=self.user)
                self.fields['investor'].initial = self.user.investor_profile
                self.fields['investor'].widget = forms.HiddenInput()
            else:
                self.fields['investor'].queryset = InvestorProfile.objects.none()

        # 2. Dynamic Folio & Mandate Filtering
        investor_id = self.data.get('investor') or (self.initial.get('investor').id if hasattr(self.initial.get('investor'), 'id') else self.initial.get('investor'))

        # If user is investor, force investor_id
        if self.user and self.user.user_type == 'INVESTOR':
            investor_id = self.user.investor_profile.id

        if investor_id:
             self.fields['folio_selection'].queryset = Folio.objects.filter(investor_id=investor_id)
             self.fields['mandate'].queryset = Mandate.objects.filter(investor_id=investor_id, status=Mandate.APPROVED)
        else:
             self.fields['mandate'].queryset = Mandate.objects.none()

        # Filter folios by scheme if selected
        scheme_id = self.data.get('scheme') or (self.initial.get('scheme').id if hasattr(self.initial.get('scheme'), 'id') else self.initial.get('scheme'))
        if investor_id and scheme_id:
            try:
                scheme = Scheme.objects.get(pk=scheme_id)
                self.fields['folio_selection'].queryset = self.fields['folio_selection'].queryset.filter(amc=scheme.amc)
            except (ValueError, Scheme.DoesNotExist):
                pass

        # Style widgets
        for field in self.fields:
            if field != 'investor' or (self.user and self.user.user_type != 'INVESTOR'):
                 self.fields[field].widget.attrs.update({'class': 'form-select'})
            if field == 'amount':
                 self.fields[field].widget.attrs.update({'class': 'form-input'})


    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        scheme = cleaned_data.get('scheme')
        txn_type = cleaned_data.get('transaction_type')
        mandate = cleaned_data.get('mandate')

        # Safety Check: If scheme is missing (invalid ID), don't proceed with dependent checks
        if not scheme:
            # Error is already added by field validation (required=True by default)
            return cleaned_data

        if amount:
            if amount < scheme.min_purchase_amount:
                self.add_error('amount', f"Minimum purchase amount is {scheme.min_purchase_amount}")
            if scheme.max_purchase_amount > 0 and amount > scheme.max_purchase_amount:
                 self.add_error('amount', f"Maximum purchase amount is {scheme.max_purchase_amount}")

        if txn_type == Order.SIP:
            if not scheme.is_sip_allowed:
                 self.add_error('scheme', "This scheme does not allow SIP investments.")
            if not mandate:
                 self.add_error('mandate', "Mandate is required for SIP registration.")

        return cleaned_data
