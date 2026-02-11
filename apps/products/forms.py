from django import forms

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
