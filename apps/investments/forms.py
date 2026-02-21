from django import forms
from .models import Order, Folio, Mandate, SIP
from apps.users.models import InvestorProfile, BankAccount
from apps.products.models import Scheme
from apps.reconciliation.models import Holding
from django.core.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta

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

    # Switch Specific Fields
    switch_mode = forms.ChoiceField(
        choices=[('AMOUNT', 'By Amount'), ('UNITS', 'By Units'), ('ALL', 'Switch All Units')],
        required=False,
        label="Switch Mode",
        widget=forms.RadioSelect
    )

    # Override amount to be optional (validated in clean)
    amount = forms.DecimalField(
        required=False,
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-input'})
    )

    # Override units to be optional (validated in clean)
    units = forms.DecimalField(
        required=False,
        max_digits=15,
        decimal_places=4,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'step': '0.0001'})
    )

    class Meta:
        model = Order
        fields = ['investor', 'scheme', 'target_scheme', 'amount', 'units', 'all_redeem', 'folio_selection', 'payment_mode', 'transaction_type', 'mandate']
        widgets = {
            'transaction_type': forms.RadioSelect,
            'target_scheme': forms.Select(attrs={'class': 'form-select'}),
            'units': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.0001'}),
            'all_redeem': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

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

        # Initialize target_scheme queryset (empty by default, filled via JS or POST)
        # We start with empty to avoid loading all schemes, but if data is present (POST), we need to allow validation.
        # Ideally, we should filter by AMC if scheme is selected, but for now we might leave it open or handle carefully.
        # To avoid validation errors on POST if scheme is not in initial queryset:
        if self.data:
            self.fields['target_scheme'].queryset = Scheme.objects.all()
        else:
             self.fields['target_scheme'].queryset = Scheme.objects.none()

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
            if field in ['transaction_type', 'switch_mode', 'all_redeem']:
                continue
            if field != 'investor' or (self.user and self.user.user_type != 'INVESTOR'):
                 if not 'class' in self.fields[field].widget.attrs:
                    self.fields[field].widget.attrs.update({'class': 'form-select'})
            if field in ['amount', 'units']:
                 self.fields[field].widget.attrs.update({'class': 'form-input'})


    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        scheme = cleaned_data.get('scheme')
        txn_type = cleaned_data.get('transaction_type')
        mandate = cleaned_data.get('mandate')
        target_scheme = cleaned_data.get('target_scheme')
        switch_mode = cleaned_data.get('switch_mode')
        units = cleaned_data.get('units')

        # Safety Check: If scheme is missing (invalid ID), don't proceed with dependent checks
        if not scheme:
            # Error is already added by field validation (required=True by default)
            return cleaned_data

        if txn_type == Order.PURCHASE:
             if not amount:
                 self.add_error('amount', "Amount is required for purchase.")
             elif amount:
                if amount < scheme.min_purchase_amount:
                    self.add_error('amount', f"Minimum purchase amount is {scheme.min_purchase_amount}")
                if scheme.max_purchase_amount > 0 and amount > scheme.max_purchase_amount:
                    self.add_error('amount', f"Maximum purchase amount is {scheme.max_purchase_amount}")

        elif txn_type == Order.SIP:
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

        elif txn_type == Order.SWITCH:
            if not target_scheme:
                self.add_error('target_scheme', "Target Scheme is required for Switch orders.")

            if target_scheme and scheme.amc != target_scheme.amc:
                self.add_error('target_scheme', "Source and Target schemes must belong to the same AMC.")

            if switch_mode == 'AMOUNT':
                if not amount or amount <= 0:
                    self.add_error('amount', "Amount must be greater than 0.")
            elif switch_mode == 'UNITS':
                if not units or units <= 0:
                    self.add_error('units', "Units must be greater than 0.")
            elif switch_mode == 'ALL':
                cleaned_data['all_redeem'] = True
                cleaned_data['amount'] = 0 # Ignore amount
                cleaned_data['units'] = 0 # Ignore units
            else:
                 self.add_error('switch_mode', "Please select a switch mode.")

        # Ensure defaults for optional fields to satisfy DB NOT NULL constraints
        if not cleaned_data.get('amount'):
            cleaned_data['amount'] = 0
        if not cleaned_data.get('units'):
            cleaned_data['units'] = 0

        return cleaned_data

class MandateForm(forms.ModelForm):
    class Meta:
        model = Mandate
        fields = ['investor', 'mandate_type', 'bank_account', 'amount_limit', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'amount_limit': forms.NumberInput(attrs={'class': 'form-input'}),
            'mandate_type': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Prefill Dates: Current Date and Current Date + 39 Years
        if not self.initial.get('start_date'):
            self.initial['start_date'] = date.today()
        if not self.initial.get('end_date'):
            self.initial['end_date'] = date.today() + relativedelta(years=39)

        # Restrict Mandate Type to E-Mandate (Net Banking) only as per BSE requirement
        self.fields['mandate_type'].choices = [
            (Mandate.NET_BANKING, 'E-Mandate (Net Banking)')
        ]
        self.fields['mandate_type'].initial = Mandate.NET_BANKING

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

class RedemptionForm(forms.Form):
    redemption_type = forms.ChoiceField(
        choices=[('AMOUNT', 'By Amount'), ('UNITS', 'By Units'), ('ALL', 'Redeem All')],
        widget=forms.RadioSelect,
        initial='AMOUNT'
    )
    value = forms.DecimalField(
        required=False,
        max_digits=15,
        decimal_places=4,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'step': '0.0001'})
    )
    all_redeem = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )

    def __init__(self, *args, **kwargs):
        self.holding = kwargs.pop('holding', None)
        if 'instance' in kwargs:
            kwargs.pop('instance')
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        red_type = cleaned_data.get('redemption_type')
        value = cleaned_data.get('value')
        all_redeem = cleaned_data.get('all_redeem')

        if not self.holding:
            raise ValidationError("Holding context missing.")

        if red_type == 'ALL':
            cleaned_data['all_redeem'] = True
            cleaned_data['value'] = 0 # Ignored
        elif red_type == 'AMOUNT':
            if not value or value <= 0:
                self.add_error('value', "Amount must be greater than 0.")
            if self.holding.current_value and value > self.holding.current_value:
                 self.add_error('value', f"Amount exceeds current holding value ({self.holding.current_value:.2f}).")
        elif red_type == 'UNITS':
            if not value or value <= 0:
                self.add_error('value', "Units must be greater than 0.")
            if value > self.holding.units:
                 self.add_error('value', f"Units exceed current holding units ({self.holding.units:.4f}).")

        return cleaned_data
