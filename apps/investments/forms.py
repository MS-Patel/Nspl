from django import forms
from .models import Order, Folio, Mandate, SIP
from apps.users.models import InvestorProfile, BankAccount
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

    # SIP Specific Fields (Not part of Order model, but needed for SIP logic)
    sip_frequency = forms.ChoiceField(
        choices=SIP.FREQUENCY_CHOICES,
        required=False,
        label="SIP Frequency",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    sip_start_date = forms.DateField(
        required=False,
        label="SIP Start Date",
        widget=forms.DateInput(attrs={'class': 'form-input', 'type': 'date'})
    )
    sip_installments = forms.IntegerField(
        required=False,
        label="No. of Installments",
        widget=forms.NumberInput(attrs={'class': 'form-input'})
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
             # Mandates should be approved to use
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
                 if not 'class' in self.fields[field].widget.attrs:
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

            # Validate SIP specific fields
            if not cleaned_data.get('sip_frequency'):
                self.add_error('sip_frequency', "Frequency is required for SIP.")
            if not cleaned_data.get('sip_start_date'):
                self.add_error('sip_start_date', "Start Date is required for SIP.")
            if not cleaned_data.get('sip_installments'):
                self.add_error('sip_installments', "Installments count is required.")

        return cleaned_data

class MandateForm(forms.ModelForm):
    class Meta:
        model = Mandate
        fields = ['investor', 'bank_account', 'amount_limit', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'amount_limit': forms.NumberInput(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            if self.user.user_type == 'DISTRIBUTOR':
                self.fields['investor'].queryset = InvestorProfile.objects.filter(distributor__user=self.user)
            elif self.user.user_type == 'RM':
                self.fields['investor'].queryset = InvestorProfile.objects.filter(distributor__rm__user=self.user)
            elif self.user.user_type == 'ADMIN':
                self.fields['investor'].queryset = InvestorProfile.objects.all()
            elif self.user.user_type == 'INVESTOR':
                self.fields['investor'].queryset = InvestorProfile.objects.filter(user=self.user)
                self.fields['investor'].initial = self.user.investor_profile
                self.fields['investor'].widget = forms.HiddenInput()
            else:
                self.fields['investor'].queryset = InvestorProfile.objects.none()

        # Dynamic Bank Filtering
        investor_id = self.data.get('investor') or (self.initial.get('investor').id if hasattr(self.initial.get('investor'), 'id') else self.initial.get('investor'))

        if self.user and self.user.user_type == 'INVESTOR':
            investor_id = self.user.investor_profile.id

        if investor_id:
             self.fields['bank_account'].queryset = BankAccount.objects.filter(investor_id=investor_id)
        else:
             self.fields['bank_account'].queryset = BankAccount.objects.none()

        # Styling
        self.fields['investor'].widget.attrs.update({'class': 'form-select'})
        self.fields['bank_account'].widget.attrs.update({'class': 'form-select'})
