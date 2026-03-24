from django import forms
from .models import SystemConfiguration

class SystemConfigurationForm(forms.ModelForm):
    class Meta:
        model = SystemConfiguration
        fields = '__all__'
        widgets = {
            'rta_email_password': forms.PasswordInput(render_value=True),
            'email_host_password': forms.PasswordInput(render_value=True),
            'company_address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.CheckboxInput,)):
                 field.widget.attrs.update({'class': 'form-checkbox is-basic size-5 rounded-sm border-slate-400/70 checked:bg-primary checked:border-primary hover:border-primary focus:border-primary dark:border-navy-400 dark:checked:bg-accent dark:checked:border-accent dark:hover:border-accent dark:focus:border-accent'})
            else:
                field.widget.attrs.update({
                    'class': 'form-input w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent'
                })
