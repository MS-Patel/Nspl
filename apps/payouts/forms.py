from django import forms
from django.core.exceptions import ValidationError
from .models import BrokerageImport

class BrokerageUploadForm(forms.ModelForm):
    class Meta:
        model = BrokerageImport
        fields = ['month', 'year', 'cams_file', 'karvy_file']
        widgets = {
            'month': forms.Select(attrs={'class': 'form-select w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent'}),
            'year': forms.NumberInput(attrs={'class': 'form-input w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent', 'placeholder': 'YYYY'}),
            'cams_file': forms.FileInput(attrs={'class': 'hidden', 'accept': '.dbf,.csv'}),
            'karvy_file': forms.FileInput(attrs={'class': 'hidden', 'accept': '.csv'}),
        }

    def clean_cams_file(self):
        file = self.cleaned_data.get('cams_file')
        if file:
            filename = file.name.lower()
            if not (filename.endswith('.dbf') or filename.endswith('.csv')):
                raise ValidationError('CAMS file must be a .dbf or .csv file.')
        return file

    def clean_karvy_file(self):
        file = self.cleaned_data.get('karvy_file')
        if file:
            filename = file.name.lower()
            if not filename.endswith('.csv'):
                raise ValidationError('Karvy file must be a .csv file.')
        return file
