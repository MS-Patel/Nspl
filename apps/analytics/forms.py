from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from .models import Goal, GoalMapping, CASUpload
from apps.reconciliation.models import Holding
from apps.users.models import User

class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['name', 'target_amount', 'target_date', 'category', 'investor']
        widgets = {
            'target_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Retirement'}),
            'target_amount': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '0.00'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'investor': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # If user is an Investor, hide the investor field and set it automatically in view
        if user and user.user_type == 'INVESTOR':
            self.fields.pop('investor')
        # If Distributor, filter investors to only those they manage
        elif user and user.user_type == 'DISTRIBUTOR':
            self.fields['investor'].queryset = user.distributor_profile.investors.all()
        # Admin can see all (default)

class GoalMappingForm(forms.ModelForm):
    class Meta:
        model = GoalMapping
        fields = ['holding', 'allocation_percentage']
        widgets = {
            'holding': forms.Select(attrs={'class': 'form-select'}),
            'allocation_percentage': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'max': 100}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default to empty to prevent leakage. View must set this explicitly.
        self.fields['holding'].queryset = Holding.objects.none()

class BaseGoalMappingFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        # Allow passing 'user' or 'investor' context if needed, but standard FormSet
        # doesn't easily propagate kwargs to forms without custom logic.
        # Instead, we will handle queryset filtering in the View by iterating forms.
        super().__init__(*args, **kwargs)

GoalMappingFormSet = inlineformset_factory(
    Goal,
    GoalMapping,
    form=GoalMappingForm,
    formset=BaseGoalMappingFormSet,
    extra=1,
    can_delete=True
)

class CASUploadForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'PDF Password (usually PAN)'}),
        required=True,
        help_text="Enter the password to open the CAS PDF (usually your PAN)."
    )

    class Meta:
        model = CASUpload
        fields = ['file', 'investor']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-input file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20'}),
            'investor': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # By default hide investor, we show it only if needed
        # But fields are declarative.

        if user:
            if user.user_type == 'INVESTOR':
                self.fields.pop('investor')
            elif user.user_type == 'DISTRIBUTOR':
                self.fields['investor'].queryset = user.distributor_profile.investors.all()
            # Admin sees all (default queryset)
        else:
            # Fallback if no user passed, hide to be safe or show empty
            self.fields.pop('investor', None)
