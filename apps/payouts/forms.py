from django import forms
from django.core.exceptions import ValidationError
from .models import BrokerageImport
import datetime

class BrokerageUploadForm(forms.ModelForm):
    month_year = forms.CharField(
        widget=forms.TextInput(attrs={
            'type': 'month',
            'class': 'form-input w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent'
        }),
        label="Select Month & Year"
    )

    class Meta:
        model = BrokerageImport
        fields = ['month_year', 'cams_file', 'karvy_file']
        widgets = {
            'cams_file': forms.FileInput(attrs={'class': 'hidden', 'accept': '.dbf,.csv'}),
            'karvy_file': forms.FileInput(attrs={'class': 'hidden', 'accept': '.csv'}),
        }

    def clean_month_year(self):
        data = self.cleaned_data['month_year']
        try:
            # Format from input type="month" is typically "YYYY-MM"
            date_obj = datetime.datetime.strptime(data, '%Y-%m')
            return date_obj
        except ValueError:
            raise ValidationError("Invalid date format. Please use YYYY-MM.")

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

    def save(self, commit=True):
        instance = super(BrokerageUploadForm, self).save(commit=False)
        month_year = self.cleaned_data['month_year']
        instance.month = month_year.month
        instance.year = month_year.year
        if commit:
            instance.save()
        return instance
