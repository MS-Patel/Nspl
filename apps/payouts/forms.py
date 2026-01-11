from django import forms
from django.forms import inlineformset_factory
from .models import CommissionRule, CommissionTier

class CommissionRuleForm(forms.ModelForm):
    class Meta:
        model = CommissionRule
        fields = ['category', 'amc']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent'}),
            'amc': forms.Select(attrs={'class': 'tom-select w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        amc = cleaned_data.get('amc')

        # Check for uniqueness manually because unique_together might ignore NULLs depending on DB
        qs = CommissionRule.objects.filter(category=category, amc=amc)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(f"A rule for {category} and {'this AMC' if amc else 'All AMCs'} already exists.")

        return cleaned_data

class CommissionTierForm(forms.ModelForm):
    class Meta:
        model = CommissionTier
        fields = ['min_aum', 'max_aum', 'rate']
        widgets = {
            'min_aum': forms.NumberInput(attrs={'class': 'form-input w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent'}),
            'max_aum': forms.NumberInput(attrs={'class': 'form-input w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent', 'placeholder': 'Leave empty for Infinity'}),
            'rate': forms.NumberInput(attrs={'class': 'form-input w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent'}),
        }

CommissionTierFormSet = inlineformset_factory(
    CommissionRule,
    CommissionTier,
    form=CommissionTierForm,
    extra=1,
    can_delete=True
)
