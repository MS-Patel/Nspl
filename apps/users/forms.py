from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.core.validators import RegexValidator
from .models import RMProfile, DistributorProfile, InvestorProfile, BankAccount, Nominee, Document, Branch
from .constants import STATE_CHOICES
from datetime import date

User = get_user_model()

# --- Validators ---
pan_validator = RegexValidator(
    regex=r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$',
    message="Enter a valid PAN (e.g., ABCDE1234F)."
)

mobile_validator = RegexValidator(
    regex=r'^[6-9]\d{9}$',
    message="Enter a valid 10-digit mobile number starting with 6-9."
)

pincode_validator = RegexValidator(
    regex=r'^[1-9][0-9]{5}$',
    message="Enter a valid 6-digit Pincode."
)

ifsc_validator = RegexValidator(
    regex=r'^[A-Z]{4}0[A-Z0-9]{6}$',
    message="Enter a valid IFSC Code (e.g., HDFC0001234)."
)

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
    branch = forms.ModelChoiceField(queryset=Branch.objects.all(), required=False)

    # Address Details
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    city = forms.CharField(max_length=50, required=False)
    pincode = forms.CharField(max_length=6, validators=[pincode_validator], required=False)
    state = forms.ChoiceField(choices=STATE_CHOICES, required=False)
    country = forms.CharField(max_length=50, initial='India', required=False)

    # Contact Details
    alternate_mobile = forms.CharField(max_length=15, required=False, validators=[mobile_validator])
    alternate_email = forms.EmailField(required=False)

    # Personal / Business Details
    dob = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label="Date of Birth")
    gstin = forms.CharField(max_length=15, required=False, label="GSTIN")

    # Bank Details
    bank_name = forms.CharField(max_length=100, required=False)
    account_number = forms.CharField(max_length=20, required=False)
    ifsc_code = forms.CharField(max_length=11, validators=[ifsc_validator], required=False)
    account_type = forms.ChoiceField(choices=RMProfile.ACCOUNT_TYPES, required=False)
    branch_name = forms.CharField(max_length=100, required=False)

    # Status
    is_active = forms.BooleanField(initial=True, required=False, label="Active Status")

    def save(self, commit=True):
        with transaction.atomic():
            user = super().save(commit=False)
            user.user_type = User.Types.RM
            user.is_active = self.cleaned_data['is_active']
            if commit:
                user.save()
                RMProfile.objects.create(
                    user=user,
                    employee_code=self.cleaned_data['employee_code'],
                    branch=self.cleaned_data.get('branch'),
                    address=self.cleaned_data.get('address', ''),
                    city=self.cleaned_data.get('city', ''),
                    pincode=self.cleaned_data.get('pincode', ''),
                    state=self.cleaned_data.get('state', ''),
                    country=self.cleaned_data.get('country', ''),
                    alternate_mobile=self.cleaned_data.get('alternate_mobile', ''),
                    alternate_email=self.cleaned_data.get('alternate_email', ''),
                    dob=self.cleaned_data.get('dob'),
                    gstin=self.cleaned_data.get('gstin', ''),
                    bank_name=self.cleaned_data.get('bank_name', ''),
                    account_number=self.cleaned_data.get('account_number', ''),
                    ifsc_code=self.cleaned_data.get('ifsc_code', ''),
                    account_type=self.cleaned_data.get('account_type', 'SB'),
                    branch_name=self.cleaned_data.get('branch_name', ''),
                    is_active=self.cleaned_data['is_active']
                )
        return user

class RMChangeForm(forms.ModelForm):
    # User fields
    name = forms.CharField(max_length=255, required=True, label="Full Name")
    email = forms.EmailField(required=True, label="Email Address")

    # Profile fields (Redefined from ModelForm to control order/widgets)
    employee_code = forms.CharField(max_length=50)
    branch = forms.ModelChoiceField(queryset=Branch.objects.all(), required=False)

    dob = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label="Date of Birth")
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)

    is_active = forms.BooleanField(required=False, label="Active Status")

    class Meta:
        model = RMProfile
        fields = [
            'employee_code', 'branch', 'dob', 'gstin',
            'address', 'city', 'state', 'pincode', 'country',
            'alternate_mobile', 'alternate_email',
            'bank_name', 'account_number', 'ifsc_code', 'account_type', 'branch_name',
            'is_active'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['name'].initial = self.instance.user.name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        with transaction.atomic():
            # Update User
            user = self.instance.user
            user.name = self.cleaned_data['name']
            user.email = self.cleaned_data['email']
            # Sync is_active
            user.is_active = self.cleaned_data['is_active']
            user.save()

            # Update Profile
            return super().save(commit=commit)

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

    # Allow Admin to select RM
    rm = forms.ModelChoiceField(
        queryset=RMProfile.objects.all(),
        required=False,
        label="Relationship Manager"
    )

    # Address Details
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    city = forms.CharField(max_length=50, required=False)
    pincode = forms.CharField(max_length=6, validators=[pincode_validator], required=False)
    state = forms.ChoiceField(choices=STATE_CHOICES, required=False)
    country = forms.CharField(max_length=50, initial='India', required=False)

    # Contact Details
    alternate_mobile = forms.CharField(max_length=15, required=False, validators=[mobile_validator])
    alternate_email = forms.EmailField(required=False)

    # Personal / Business Details
    dob = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label="Date of Birth / Incorporation")
    gstin = forms.CharField(max_length=15, required=False, label="GSTIN")

    # Bank Details
    bank_name = forms.CharField(max_length=100, required=False)
    account_number = forms.CharField(max_length=20, required=False)
    ifsc_code = forms.CharField(max_length=11, validators=[ifsc_validator], required=False)
    account_type = forms.ChoiceField(choices=DistributorProfile.ACCOUNT_TYPES, required=False)
    branch_name = forms.CharField(max_length=100, required=False)

    # Status
    is_active = forms.BooleanField(initial=True, required=False, label="Active Status")

    def __init__(self, *args, **kwargs):
        self.rm_user = kwargs.pop('rm_user', None)
        super().__init__(*args, **kwargs)
        # If created by RM, hide the RM field or set it to self
        if self.rm_user and self.rm_user.user_type == User.Types.RM:
            self.fields['rm'].widget = forms.HiddenInput()

    def save(self, commit=True):
        with transaction.atomic():
            user = super().save(commit=False)
            user.user_type = User.Types.DISTRIBUTOR
            user.is_active = self.cleaned_data['is_active']
            if commit:
                user.save()

                # Determine RM: if creator is RM, use them. Else use selected RM.
                rm_profile = self.cleaned_data.get('rm')
                if self.rm_user and self.rm_user.user_type == User.Types.RM:
                    rm_profile = self.rm_user.rm_profile

                DistributorProfile.objects.create(
                    user=user,
                    rm=rm_profile,
                    parent=self.cleaned_data.get('parent_distributor'),
                    arn_number=self.cleaned_data['arn_number'],
                    euin=self.cleaned_data.get('euin', ''),
                    pan=self.cleaned_data.get('pan', ''),
                    mobile=self.cleaned_data.get('mobile', ''),
                    address=self.cleaned_data.get('address', ''),
                    city=self.cleaned_data.get('city', ''),
                    pincode=self.cleaned_data.get('pincode', ''),
                    state=self.cleaned_data.get('state', ''),
                    country=self.cleaned_data.get('country', ''),
                    alternate_mobile=self.cleaned_data.get('alternate_mobile', ''),
                    alternate_email=self.cleaned_data.get('alternate_email', ''),
                    dob=self.cleaned_data.get('dob'),
                    gstin=self.cleaned_data.get('gstin', ''),
                    bank_name=self.cleaned_data.get('bank_name', ''),
                    account_number=self.cleaned_data.get('account_number', ''),
                    ifsc_code=self.cleaned_data.get('ifsc_code', ''),
                    account_type=self.cleaned_data.get('account_type', 'SB'),
                    branch_name=self.cleaned_data.get('branch_name', ''),
                    is_active=self.cleaned_data['is_active']
                )
        return user

class DistributorChangeForm(forms.ModelForm):
    # User fields
    name = forms.CharField(max_length=255, required=True, label="Full Name")
    email = forms.EmailField(required=True, label="Email Address")

    # Profile fields
    arn_number = forms.CharField(max_length=50)
    parent = forms.ModelChoiceField(queryset=DistributorProfile.objects.all(), required=False, label="Parent Distributor")
    rm = forms.ModelChoiceField(queryset=RMProfile.objects.all(), required=False, label="Relationship Manager")

    dob = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label="Date of Birth / Incorporation")
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)

    is_active = forms.BooleanField(required=False, label="Active Status")

    class Meta:
        model = DistributorProfile
        fields = [
            'arn_number', 'euin', 'pan', 'mobile',
            'parent', 'rm',
            'dob', 'gstin',
            'address', 'city', 'state', 'pincode', 'country',
            'alternate_mobile', 'alternate_email',
            'bank_name', 'account_number', 'ifsc_code', 'account_type', 'branch_name',
            'is_active'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['name'].initial = self.instance.user.name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        with transaction.atomic():
            # Update User
            user = self.instance.user
            user.name = self.cleaned_data['name']
            user.email = self.cleaned_data['email']
            user.is_active = self.cleaned_data['is_active']
            user.save()

            # Update Profile
            return super().save(commit=commit)

class UserProfileForm(forms.ModelForm):
    name = forms.CharField(max_length=255, required=True, label="Full Name")
    email = forms.EmailField(required=True, label="Email Address")

    class Meta:
        model = User
        fields = ['name', 'email']

class RMProfileUpdateForm(forms.ModelForm):
    # Keep this for RM self-update if needed, but restrict fields
    employee_code = forms.CharField(max_length=50, disabled=True, required=False, help_text="Cannot be changed.")
    branch = forms.ModelChoiceField(queryset=Branch.objects.all(), disabled=True, required=False, help_text="Cannot be changed.")

    class Meta:
        model = RMProfile
        fields = ['employee_code', 'branch']

class DistributorProfileUpdateForm(forms.ModelForm):
    # Keep this for Distributor self-update
    arn_number = forms.CharField(max_length=50, disabled=True, required=False, help_text="Cannot be changed.")
    euin = forms.CharField(max_length=50, required=False)
    pan = forms.CharField(max_length=10, required=False)
    mobile = forms.CharField(max_length=15, required=False)

    class Meta:
        model = DistributorProfile
        fields = ['arn_number', 'euin', 'pan', 'mobile']

class InvestorCreationForm(UserCreationForm):
    """
    Simple form for basic investor creation. Kept for backward compatibility or simple adds.
    """
    firstname = forms.CharField(max_length=100)
    middlename = forms.CharField(max_length=100, required=False)
    lastname = forms.CharField(max_length=100, required=False)
    pan = forms.CharField(max_length=10, validators=[pan_validator])
    dob = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    gender = forms.ChoiceField(choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], required=False)
    mobile = forms.CharField(max_length=15, required=False, validators=[mobile_validator])
    address = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, **kwargs):
        self.distributor_user = kwargs.pop('distributor_user', None)
        super().__init__(*args, **kwargs)
        if 'name' in self.fields:
            del self.fields['name']

    def save(self, commit=True):
        with transaction.atomic():
            user = super().save(commit=False)
            user.user_type = User.Types.INVESTOR

            # Construct full name
            fname = self.cleaned_data.get('firstname', '').strip()
            mname = self.cleaned_data.get('middlename', '').strip()
            lname = self.cleaned_data.get('lastname', '').strip()
            user.name = f"{fname} {mname} {lname}".replace('  ', ' ').strip()

            if commit:
                user.save()

                distributor_profile = None
                if self.distributor_user and self.distributor_user.user_type == User.Types.DISTRIBUTOR:
                    distributor_profile = self.distributor_user.distributor_profile

                InvestorProfile.objects.create(
                    user=user,
                    distributor=distributor_profile,
                    firstname=fname,
                    middlename=mname,
                    lastname=lname,
                    pan=self.cleaned_data['pan'],
                    dob=self.cleaned_data.get('dob'),
                    gender=self.cleaned_data.get('gender', ''),
                    mobile=self.cleaned_data.get('mobile', ''),
                    address_1=self.cleaned_data.get('address', '')
                )
        return user

class InvestorProfileForm(forms.ModelForm):
    """
    Comprehensive form for Investor Profile, used in the Onboarding Wizard and Update View.
    Includes User fields (name, email) managed manually or via a mixin.
    """
    # User fields
    firstname = forms.CharField(max_length=100, label="First Name")
    middlename = forms.CharField(max_length=100, required=False, label="Middle Name")
    lastname = forms.CharField(max_length=100, required=False, label="Last Name")
    email = forms.EmailField(label="Email Address")

    # Validated fields
    pan = forms.CharField(max_length=10, validators=[pan_validator])
    mobile = forms.CharField(max_length=15, validators=[mobile_validator])
    pincode = forms.CharField(max_length=6, validators=[pincode_validator])

    # Date widget override
    dob = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)

    # State Dropdown
    state = forms.ChoiceField(choices=STATE_CHOICES, required=False)
    foreign_state = forms.ChoiceField(choices=STATE_CHOICES, required=False, label="Foreign State")

    # Hierarchy Fields (for Assignment)
    # Explicitly declared to control order or attributes, though they are in Meta.fields
    distributor = forms.ModelChoiceField(queryset=DistributorProfile.objects.all(), required=False)
    rm = forms.ModelChoiceField(queryset=RMProfile.objects.all(), required=False, label="Relationship Manager")
    branch = forms.ModelChoiceField(queryset=Branch.objects.all(), required=False)

    class Meta:
        model = InvestorProfile
        fields = [
            'firstname', 'middlename', 'lastname',
            'pan', 'dob', 'gender', 'mobile',
            'tax_status', 'occupation', 'holding_nature',
            'address_1', 'address_2', 'address_3', 'city', 'state', 'pincode', 'country',

            # Hierarchy
            'distributor', 'rm', 'branch',

            # FATCA
            'place_of_birth', 'country_of_birth', 'source_of_wealth', 'income_slab', 'pep_status', 'exemption_code',

            # Foreign Address
            'foreign_address_1', 'foreign_address_2', 'foreign_address_3',
            'foreign_city', 'foreign_state', 'foreign_pincode', 'foreign_country',
            'foreign_resi_phone', 'foreign_res_fax', 'foreign_off_phone', 'foreign_off_fax',

            # Guardian
            'guardian_name', 'guardian_pan', 'guardian_kyc_type', 'guardian_ckyc_number',
            'guardian_relationship', 'guardian_kra_exempt_ref_no',

            # Joint Holders
            'second_applicant_name', 'second_applicant_pan', 'second_applicant_dob',
            'second_applicant_email', 'second_applicant_mobile', 'second_applicant_kyc_type',
            'second_applicant_ckyc_number', 'second_applicant_kra_exempt_ref_no',
            'second_applicant_email_declaration', 'second_applicant_mobile_declaration',

            'third_applicant_name', 'third_applicant_pan', 'third_applicant_dob',
            'third_applicant_email', 'third_applicant_mobile', 'third_applicant_kyc_type',
            'third_applicant_ckyc_number', 'third_applicant_kra_exempt_ref_no',
            'third_applicant_email_declaration', 'third_applicant_mobile_declaration',

            # Demat
            'client_type', 'depository', 'dp_id', 'client_id',

            # Misc V183
            'kyc_type', 'ckyc_number', 'kra_exempt_ref_no',
            'mobile_declaration', 'email_declaration',
            'nomination_opt', 'nomination_auth_mode',
            'lei_no', 'lei_validity', 'mapin_id', 'paperless_flag'
        ]
        widgets = {
            'lei_validity': forms.DateInput(attrs={'type': 'date'}),
            'second_applicant_dob': forms.DateInput(attrs={'type': 'date'}),
            'third_applicant_dob': forms.DateInput(attrs={'type': 'date'}),
            'nomination_auth_mode': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('user', None) # Pass request.user for logic
        super().__init__(*args, **kwargs)

        # Restrict Nomination Auth Mode to Online OTP only
        self.fields['nomination_auth_mode'].choices = [
            (InvestorProfile.ONLINE_OTP, 'Online/OTP')
        ]
        self.fields['nomination_auth_mode'].initial = InvestorProfile.ONLINE_OTP

        # Populate initial user data if instance exists
        if self.instance and self.instance.pk and self.instance.user:
            self.fields['email'].initial = self.instance.user.email

        # Ensure firstname/middle/last are populated from instance (ModelForm does this automatically for model fields)

        # Permissions Logic for Hierarchy Fields
        if self.request_user:
            if self.request_user.user_type == User.Types.INVESTOR:
                # Investors cannot change their mapping
                self.fields['distributor'].disabled = True
                self.fields['rm'].disabled = True
                self.fields['branch'].disabled = True
            elif self.request_user.user_type == User.Types.DISTRIBUTOR:
                 # Distributor cannot change their own mapping via this form usually, or only see self
                 self.fields['distributor'].disabled = True
                 self.fields['rm'].disabled = True
                 self.fields['branch'].disabled = True
            elif self.request_user.user_type == User.Types.RM:
                # RM can assign distributor (from their list potentially)
                # RM cannot change RM (assign to another RM? Maybe not allowed or only to self)
                # RM cannot change Branch (bound to RM)

                # Logic: RM can set Distributor to one of their own distributors or None (Direct)
                self.fields['distributor'].queryset = DistributorProfile.objects.filter(rm__user=self.request_user)

                # RM field: Can they reassign to another RM? User requirement: "assign distributor to investor... at RM level"
                # It doesn't explicitly say reassignment to another RM. usually RM manages THEIR investors.
                # So we lock RM to self (or current value) and Branch to self's branch.
                self.fields['rm'].disabled = True
                self.fields['branch'].disabled = True

            # Admin has full access (default)

    def clean(self):
        cleaned_data = super().clean()
        dob = cleaned_data.get("dob")

        if dob:
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

            if age < 18:
                # Is Minor
                guardian_name = cleaned_data.get("guardian_name")
                guardian_pan = cleaned_data.get("guardian_pan")

                if not guardian_name:
                    self.add_error('guardian_name', "Guardian Name is required for minor investor.")

                if not guardian_pan:
                    self.add_error('guardian_pan', "Guardian PAN is required for minor investor.")

                # Enforce Tax Status
                tax_status = cleaned_data.get("tax_status")
                if tax_status != InvestorProfile.MINOR:
                     self.add_error('tax_status', "Tax Status must be 'On Behalf of Minor' for investors under 18.")

        return cleaned_data

    def clean_pan(self):
        pan = self.cleaned_data.get('pan')
        if pan:
            # If this is a new instance (create), check if User already exists with this PAN
            if not self.instance.pk:
                if User.objects.filter(username=pan).exists():
                    raise forms.ValidationError(f"User with PAN {pan} already exists.")
        return pan

class BankAccountForm(forms.ModelForm):
    ifsc_code = forms.CharField(max_length=11, validators=[ifsc_validator])

    class Meta:
        model = BankAccount
        fields = ['ifsc_code', 'account_number', 'account_type', 'bank_name', 'branch_name', 'is_default']

class NomineeForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date of Birth (Required if Minor)"
    )
    guardian_pan = forms.CharField(max_length=10, required=False, validators=[pan_validator])

    # State Dropdown
    state = forms.ChoiceField(choices=STATE_CHOICES, required=False)

    class Meta:
        model = Nominee
        fields = [
            'name', 'relationship', 'percentage', 'date_of_birth',
            'guardian_name', 'guardian_pan', 'pan',
            'address_1', 'address_2', 'address_3', 'city', 'state', 'pincode', 'country', 'mobile', 'email',
            'id_type', 'id_number'
        ]
        widgets = {
            'relationship': forms.Select(),
        }

class BaseNomineeFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        total_percentage = 0
        has_forms = False

        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                continue

            has_forms = True
            percentage = form.cleaned_data.get('percentage', 0)
            total_percentage += percentage

            # Check for Minor
            dob = form.cleaned_data.get('date_of_birth')
            if dob:
                today = date.today()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                if age < 18:
                    if not form.cleaned_data.get('guardian_name'):
                        form.add_error('guardian_name', "Guardian Name is required for minor nominee.")
                    if not form.cleaned_data.get('guardian_pan'):
                        form.add_error('guardian_pan', "Guardian PAN is required for minor nominee.")

        if has_forms and total_percentage != 100:
             raise forms.ValidationError(f"Total Nominee Percentage must be 100%. Currently it is {total_percentage}%.")

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['document_type', 'file', 'description']

# Formsets
BankAccountFormSet = inlineformset_factory(
    InvestorProfile,
    BankAccount,
    form=BankAccountForm,
    extra=1,
    can_delete=True
)

NomineeFormSet = inlineformset_factory(
    InvestorProfile,
    Nominee,
    form=NomineeForm,
    formset=BaseNomineeFormSet,
    extra=1,
    can_delete=True
)

class InvestorUploadForm(forms.Form):
    file = forms.FileField(
        label='Investor CSV File',
        help_text='CSV file with columns: PAN, Firstname, Middlename, Lastname, Email, Mobile, etc.'
    )

class DistributorUploadForm(forms.Form):
    file = forms.FileField(
        label='Distributor CSV File',
        help_text='CSV file with columns: ARN, Name, Email, Mobile, PAN, Address, Bank Details, etc.'
    )

class RMUploadForm(forms.Form):
    file = forms.FileField(
        label='RM CSV File',
        help_text='CSV/Excel file with columns: Employee Code, Name, Email, Branch Code, Address, Bank Details, etc.'
    )
