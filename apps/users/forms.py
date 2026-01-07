from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import RMProfile, DistributorProfile, InvestorProfile

User = get_user_model()

class UserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'name', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("passwords do not match")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class RMCreationForm(UserCreationForm):
    employee_code = forms.CharField(max_length=50)

    def save(self, commit=True):
        with transaction.atomic():
            user = super().save(commit=False)
            user.user_type = User.Types.RM
            if commit:
                user.save()
                RMProfile.objects.create(
                    user=user,
                    employee_code=self.cleaned_data['employee_code']
                )
        return user

class DistributorCreationForm(UserCreationForm):
    arn_number = forms.CharField(max_length=50)
    euin = forms.CharField(max_length=50, required=False)
    pan = forms.CharField(max_length=10, required=False)
    mobile = forms.CharField(max_length=15, required=False)

    # Optional parent distributor for hierarchy
    parent_distributor = forms.ModelChoiceField(
        queryset=DistributorProfile.objects.all(),
        required=False,
        label="Parent Distributor (if sub-broker)"
    )

    def __init__(self, *args, **kwargs):
        self.rm_user = kwargs.pop('rm_user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        with transaction.atomic():
            user = super().save(commit=False)
            user.user_type = User.Types.DISTRIBUTOR
            if commit:
                user.save()

                # Determine RM: if creator is RM, use them. If Admin, it might be None or selected (simplified for now)
                rm_profile = None
                if self.rm_user and self.rm_user.user_type == User.Types.RM:
                    rm_profile = self.rm_user.rm_profile

                DistributorProfile.objects.create(
                    user=user,
                    rm=rm_profile,
                    parent=self.cleaned_data.get('parent_distributor'),
                    arn_number=self.cleaned_data['arn_number'],
                    euin=self.cleaned_data.get('euin', ''),
                    pan=self.cleaned_data.get('pan', ''),
                    mobile=self.cleaned_data.get('mobile', '')
                )
        return user

class InvestorCreationForm(UserCreationForm):
    pan = forms.CharField(max_length=10)
    dob = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    gender = forms.ChoiceField(choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], required=False)
    mobile = forms.CharField(max_length=15, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, **kwargs):
        self.distributor_user = kwargs.pop('distributor_user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        with transaction.atomic():
            user = super().save(commit=False)
            user.user_type = User.Types.INVESTOR
            if commit:
                user.save()

                distributor_profile = None
                if self.distributor_user and self.distributor_user.user_type == User.Types.DISTRIBUTOR:
                    distributor_profile = self.distributor_user.distributor_profile

                InvestorProfile.objects.create(
                    user=user,
                    distributor=distributor_profile,
                    pan=self.cleaned_data['pan'],
                    dob=self.cleaned_data.get('dob'),
                    gender=self.cleaned_data.get('gender', ''),
                    mobile=self.cleaned_data.get('mobile', ''),
                    address=self.cleaned_data.get('address', '')
                )
        return user
