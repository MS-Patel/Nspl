from django import forms
from .models import BrokerageImport

class BrokerageUploadForm(forms.ModelForm):
    class Meta:
        model = BrokerageImport
        fields = ['month', 'year', 'cams_file', 'karvy_file']
        widgets = {
            'month': forms.Select(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'YYYY'}),
            'cams_file': forms.FileInput(attrs={'class': 'form-control'}),
            'karvy_file': forms.FileInput(attrs={'class': 'form-control'}),
        }
