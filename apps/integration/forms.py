from django import forms
import re

class NDMLRegistrationForm(forms.Form):
    # Personal Details
    pan_no = forms.CharField(max_length=10, required=True, label="PAN Number",
                             widget=forms.TextInput(attrs={'class': 'form-input peer w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 pl-9 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent', 'placeholder': 'Enter PAN'}))
    name = forms.CharField(max_length=100, required=True, label="Full Name",
                           widget=forms.TextInput(attrs={'class': 'form-input peer w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 pl-9 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent', 'placeholder': 'Enter Full Name'}))
    dob = forms.DateField(required=True, label="Date of Birth (DD-MM-YYYY)", input_formats=['%d-%m-%Y'],
                          widget=forms.TextInput(attrs={'class': 'form-input peer w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 pl-9 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent', 'placeholder': 'DD-MM-YYYY'}))
    gender = forms.ChoiceField(choices=[('M', 'Male'), ('F', 'Female'), ('T', 'Transgender')], required=True, label="Gender",
                               widget=forms.Select(attrs={'class': 'form-select mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:bg-navy-700 dark:hover:border-navy-400 dark:focus:border-accent'}))
    mobile_no = forms.CharField(max_length=10, required=True, label="Mobile Number",
                                widget=forms.TextInput(attrs={'class': 'form-input peer w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 pl-9 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent', 'placeholder': '10 Digit Mobile'}))
    email = forms.EmailField(required=True, label="Email Address",
                             widget=forms.EmailInput(attrs={'class': 'form-input peer w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 pl-9 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent', 'placeholder': 'Email'}))

    # Address Details
    cor_add1 = forms.CharField(max_length=50, required=True, label="Address Line 1",
                               widget=forms.TextInput(attrs={'class': 'form-input peer w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 pl-9 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent', 'placeholder': 'Address Line 1'}))
    cor_add2 = forms.CharField(max_length=50, required=False, label="Address Line 2",
                               widget=forms.TextInput(attrs={'class': 'form-input peer w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 pl-9 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent', 'placeholder': 'Address Line 2'}))
    cor_city = forms.CharField(max_length=50, required=True, label="City",
                               widget=forms.TextInput(attrs={'class': 'form-input peer w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 pl-9 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent', 'placeholder': 'City'}))
    cor_state = forms.CharField(max_length=50, required=True, label="State",
                                widget=forms.TextInput(attrs={'class': 'form-input peer w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 pl-9 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent', 'placeholder': 'State'}))
    cor_pincode = forms.CharField(max_length=6, required=True, label="Pincode",
                                  widget=forms.TextInput(attrs={'class': 'form-input peer w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 pl-9 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent', 'placeholder': '6 Digit Pincode'}))
    cor_ctry = forms.CharField(max_length=3, required=True, initial="101", label="Country Code",
                               widget=forms.TextInput(attrs={'class': 'form-input peer w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 pl-9 placeholder:text-slate-400/70 hover:border-slate-400 focus:border-primary dark:border-navy-450 dark:hover:border-navy-400 dark:focus:border-accent', 'placeholder': '101 for India'}))

    def clean_pan_no(self):
        pan = self.cleaned_data.get('pan_no', '').upper()
        if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan):
            raise forms.ValidationError("Invalid PAN format.")
        return pan

    def clean_mobile_no(self):
        mobile = self.cleaned_data.get('mobile_no', '')
        if not re.match(r'^[0-9]{10}$', mobile):
            raise forms.ValidationError("Mobile number must be 10 digits.")
        return mobile

    def clean_cor_pincode(self):
        pincode = self.cleaned_data.get('cor_pincode', '')
        if not re.match(r'^[0-9]{6}$', pincode):
            raise forms.ValidationError("Pincode must be 6 digits.")
        return pincode
