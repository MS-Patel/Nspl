from django import forms
from django.forms import inlineformset_factory
from .models import (
    Scheme, SchemeHolding, SchemeSectorAllocation,
    SchemeAssetAllocation, SchemeManager
)

class SchemeUploadForm(forms.Form):
    file = forms.FileField(
        label='Scheme Master File',
        help_text='CSV/Pipe-separated file with standard Scheme Master columns'
    )

class NAVUploadForm(forms.Form):
    file = forms.FileField(
        label='NAV History File',
        help_text='CSV file with columns: Scheme Code, Date (DD-MM-YYYY), NAV'
    )

class SchemeForm(forms.ModelForm):
    class Meta:
        model = Scheme
        fields = [
            'name', 'scheme_code', 'isin', 'amfi_code',
            'category', 'scheme_type', 'scheme_plan',
            'start_date', 'end_date', 'reopening_date',
            'aum', 'expense_ratio', 'benchmark_index', 'riskometer', 'about_fund',
            'min_purchase_amount', 'purchase_allowed', 'redemption_allowed'
        ]
        widgets = {
            'about_fund': forms.Textarea(attrs={'rows': 4}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'reopening_date': forms.DateInput(attrs={'type': 'date'}),
        }

# Inline Formsets for dynamic row adding
SchemeHoldingFormSet = inlineformset_factory(
    Scheme, SchemeHolding,
    fields=['company_name', 'percentage'],
    extra=1,
    can_delete=True
)

SchemeSectorFormSet = inlineformset_factory(
    Scheme, SchemeSectorAllocation,
    fields=['sector_name', 'percentage'],
    extra=1,
    can_delete=True
)

SchemeAssetFormSet = inlineformset_factory(
    Scheme, SchemeAssetAllocation,
    fields=['asset_type', 'percentage'],
    extra=1,
    can_delete=True
)

SchemeManagerFormSet = inlineformset_factory(
    Scheme, SchemeManager,
    fields=['manager', 'start_date', 'is_primary'],
    widgets={'start_date': forms.DateInput(attrs={'type': 'date'})},
    extra=1,
    can_delete=True
)
