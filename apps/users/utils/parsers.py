import csv
import logging
import pandas as pd
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.users.models import InvestorProfile, DistributorProfile, RMProfile, BankAccount, Nominee, Branch
from datetime import datetime

User = get_user_model()
logger = logging.getLogger(__name__)

# --- Column Mappings ---
# Maps internal keys to possible external variations (lowercase, stripped)
DISTRIBUTOR_COLUMN_MAP = {
    'arn': ['arn', 'arn number', 'distributor arn', 'arn code', 'arn no'],
    'broker code': ['broker code', 'sub broker code', 'sub-broker code', 'broker id'],
    'name': ['name', 'distributor name', 'agent name'],
    'email': ['email', 'email id', 'email address'],
    'mobile': ['mobile', 'mobile number', 'mobile no', 'phone', 'contact number'],
    'pan': ['pan', 'pan number', 'pan no'],
    'euin': ['euin', 'euin number'],
    'parent arn (optional)': ['parent arn', 'parent arn (optional)', 'master arn'],
    'rm employee code (optional)': ['rm employee code', 'rm employee code (optional)', 'rm code', 'relationship manager code'],
}

INVESTOR_COLUMN_MAP = {
    'pan': ['pan', 'pan number', 'investor pan'],
    'first name': ['first name', 'firstname', 'f_name'],
    'middle name': ['middle name', 'middlename', 'm_name'],
    'last name': ['last name', 'lastname', 'l_name', 'surname'],
    'email': ['email', 'email id'],
    'mobile': ['mobile', 'mobile number', 'phone'],
}

RM_COLUMN_MAP = {
    'employee code': ['employee code', 'emp code', 'rm code', 'rm id'],
    'branch code': ['branch code', 'branch id'],
    'name': ['name', 'rm name'],
}

def normalize_headers(input_headers, mapping):
    """
    Normalizes a list of headers based on a mapping dictionary.
    Returns a dictionary mapping: {Original Header -> Normalized Key}
    """
    normalized_map = {}
    input_headers_lower = [h.strip().lower() for h in input_headers]

    # Pre-compute reverse mapping for O(1) lookups: {variation: standard_key}
    reverse_mapping = {}
    for key, variations in mapping.items():
        for variation in variations:
            reverse_mapping[variation] = key

    # Match input headers
    for original_header in input_headers:
        header_lower = str(original_header).strip().lower()

        # 1. Check exact match in reverse mapping
        if header_lower in reverse_mapping:
             normalized_map[original_header] = reverse_mapping[header_lower]
        else:
             # 2. Check if standard key is contained in header (fuzzy fallback)
             # Be careful with fuzzy matches (e.g., 'email' matching 'alternate email')
             # So we prioritize exact variations first.
             # If no match found, keep original or normalized lower
             normalized_map[original_header] = header_lower

    return normalized_map

def read_file_to_dicts(file_obj, column_mapping=None):
    """
    Reads a CSV or Excel file and returns a list of dictionaries with normalized keys.
    """
    data = []
    filename = file_obj.name.lower()

    try:
        # 1. Read Data into List of Dicts (Raw Headers)
        raw_data = []
        if filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file_obj)
            df = df.fillna('')
            raw_data = df.to_dict('records')
        else:
            decoded_file = file_obj.read().decode('utf-8-sig').splitlines()
            reader = csv.DictReader(decoded_file)
            raw_data = list(reader)

        if not raw_data:
            return []

        # 2. Normalize Headers
        if column_mapping:
            # Get headers from first row keys
            sample_headers = list(raw_data[0].keys())
            header_map = normalize_headers(sample_headers, column_mapping)

            # Transform Data
            normalized_data = []
            for row in raw_data:
                new_row = {}
                for k, v in row.items():
                    # Map key if possible, else use lowercase
                    new_key = header_map.get(k, str(k).strip().lower())
                    new_row[new_key] = v
                normalized_data.append(new_row)
            data = normalized_data
        else:
            # Fallback to simple lowercase normalization
            for row in raw_data:
                 data.append({str(k).strip().lower(): v for k, v in row.items()})

    except Exception as e:
        logger.error(f"Error reading file {filename}: {e}")
        raise ValueError(f"Error reading file: {str(e)}")

    return data

def get_choice_key(display_value, choices):
    """
    Finds the key for a given display value in a choices tuple list.
    If not found, returns the value as is (assuming it might be the key).
    Case-insensitive match.
    """
    if not display_value:
        return ''

    val_str = str(display_value).strip().lower()

    for key, label in choices:
        if str(label).strip().lower() == val_str:
            return key
        if str(key).strip().lower() == val_str:
            return key

    return display_value # Fallback

def parse_bool(value):
    if not value:
        return False
    val_str = str(value).strip().lower()
    return val_str in ['yes', 'y', 'true', '1']

def parse_date(value):
    """
    Parses date with priority for DD-MM-YYYY format.
    """
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            return value.date()
        # pandas to_datetime with dayfirst=True handles dd-mm-yyyy well
        return pd.to_datetime(value, dayfirst=True).date()
    except Exception:
        return None

def import_investors_from_file(file_obj):
    """
    Parses a CSV/Excel file with Investor Details.
    Supports extended fields including Bank Accounts and Nominees.
    """
    count = 0
    errors = []

    try:
        rows = read_file_to_dicts(file_obj, INVESTOR_COLUMN_MAP)

        # Validate Required Columns
        if rows and 'pan' not in rows[0]:
             # Check if 'pan' key exists in the first row (even if value is empty)
             # read_file_to_dicts ensures keys exist for all rows if from DF, but CSV DictReader might vary?
             # Actually DictReader keys are consistent.
             # If mapping failed, 'pan' key won't be there.
             return 0, ["Critical Error: 'PAN' column not found in file. Please check headers."]

        for row_idx, row in enumerate(rows, start=1):
            try:
                pan = str(row.get('pan', '')).strip().upper()
                if not pan:
                    continue # Skip empty rows

                firstname = str(row.get('first name', row.get('firstname', ''))).strip()
                middlename = str(row.get('middle name', row.get('middlename', ''))).strip()
                lastname = str(row.get('last name', row.get('lastname', ''))).strip()
                full_name = f"{firstname} {middlename} {lastname}".replace('  ', ' ').strip()

                email = str(row.get('email', '')).strip()
                mobile = str(row.get('mobile', '')).strip()

                with transaction.atomic():
                    # 1. User
                    user = None
                    try:
                        user = User.objects.get(username=pan)
                        # Update user details if exists
                        if full_name: user.name = full_name
                        if email: user.email = email
                        user.save()
                    except User.DoesNotExist:
                        user = User.objects.create_user(username=pan, email=email, password=pan, force_password_change=True)
                        user.name = full_name
                        user.user_type = User.Types.INVESTOR
                        user.save()

                    # 2. Investor Profile
                    profile, created = InvestorProfile.objects.get_or_create(user=user, defaults={'pan': pan})

                    # Update fields
                    if firstname: profile.firstname = firstname
                    if middlename: profile.middlename = middlename
                    if lastname: profile.lastname = lastname
                    if email: profile.email = email
                    if mobile: profile.mobile = mobile

                    # Map extended fields
                    profile.tax_status = get_choice_key(row.get('tax status'), InvestorProfile.TAX_STATUS_CHOICES) or profile.tax_status
                    profile.occupation = get_choice_key(row.get('occupation'), InvestorProfile.OCCUPATION_CHOICES) or profile.occupation
                    profile.holding_nature = get_choice_key(row.get('holding nature'), InvestorProfile.HOLDING_CHOICES) or profile.holding_nature
                    profile.source_of_wealth = get_choice_key(row.get('source of wealth'), InvestorProfile.SOURCE_OF_WEALTH_CHOICES) or profile.source_of_wealth
                    profile.income_slab = get_choice_key(row.get('income slab'), InvestorProfile.INCOME_SLAB_CHOICES) or profile.income_slab
                    profile.pep_status = get_choice_key(row.get('pep status'), InvestorProfile.PEP_CHOICES) or profile.pep_status

                    if row.get('place of birth'): profile.place_of_birth = row.get('place of birth')
                    if row.get('country of birth'): profile.country_of_birth = row.get('country of birth')
                    if row.get('exemption code'): profile.exemption_code = get_choice_key(row.get('exemption code'), InvestorProfile.EXEMPTION_CODE_CHOICES)

                    # Date of Birth
                    dob = parse_date(row.get('date of birth (yyyy-mm-dd)') or row.get('dob'))
                    if dob: profile.dob = dob

                    gender_val = str(row.get('gender', '')).upper()
                    if gender_val.startswith('M'): profile.gender = 'M'
                    elif gender_val.startswith('F'): profile.gender = 'F'
                    elif gender_val.startswith('O'): profile.gender = 'O'

                    # Address
                    if row.get('address 1'): profile.address_1 = str(row.get('address 1'))[:40]
                    if row.get('address 2'): profile.address_2 = str(row.get('address 2'))[:40]
                    if row.get('address 3'): profile.address_3 = str(row.get('address 3'))[:40]
                    if row.get('city'): profile.city = str(row.get('city'))[:35]
                    if row.get('state'): profile.state = str(row.get('state'))[:30]
                    if row.get('pincode'): profile.pincode = str(row.get('pincode'))[:6]
                    if row.get('country'): profile.country = str(row.get('country'))[:35]

                    # Foreign Address
                    if row.get('foreign address 1'): profile.foreign_address_1 = str(row.get('foreign address 1'))[:40]
                    if row.get('foreign address 2'): profile.foreign_address_2 = str(row.get('foreign address 2'))[:40]
                    if row.get('foreign address 3'): profile.foreign_address_3 = str(row.get('foreign address 3'))[:40]
                    if row.get('foreign city'): profile.foreign_city = str(row.get('foreign city'))[:35]
                    if row.get('foreign state'): profile.foreign_state = str(row.get('foreign state'))[:35]
                    if row.get('foreign pincode'): profile.foreign_pincode = str(row.get('foreign pincode'))[:10]
                    if row.get('foreign country'): profile.foreign_country = str(row.get('foreign country'))[:35]

                    # Demat
                    if row.get('client type'): profile.client_type = get_choice_key(row.get('client type'), InvestorProfile.CLIENT_TYPE_CHOICES)
                    if row.get('depository'): profile.depository = get_choice_key(row.get('depository'), InvestorProfile.DEPOSITORY_CHOICES)
                    if row.get('dp id'): profile.dp_id = str(row.get('dp id'))
                    if row.get('client id'): profile.client_id = str(row.get('client id'))

                    # Other
                    if row.get('ucc code'): profile.ucc_code = str(row.get('ucc code')).strip()
                    if 'is offline (y/n)' in row: profile.is_offline = parse_bool(row.get('is offline (y/n)'))

                    profile.save()

                    # 3. Nominees (1 to 3)
                    # For nominees, if columns exist, we overwrite. If not, we skip.
                    # Assuming if "nominee 1 name" is present, we should process nominees.
                    if row.get('nominee 1 name'):
                        profile.nominees.all().delete()
                        for i in range(1, 4):
                            n_name = str(row.get(f'nominee {i} name', '')).strip()
                            if n_name:
                                pct_val = row.get(f'nominee {i} %')
                                pct = 0
                                try:
                                    pct = float(pct_val) if pct_val else 0
                                except: pass

                                n_rel = row.get(f'nominee {i} relationship', 'Others')
                                n_dob = parse_date(row.get(f'nominee {i} dob'))
                                n_guardian = str(row.get(f'nominee {i} guardian', ''))

                                Nominee.objects.create(
                                    investor=profile,
                                    name=n_name,
                                    percentage=pct,
                                    relationship=n_rel,
                                    date_of_birth=n_dob,
                                    guardian_name=n_guardian
                                )

                    # 4. Bank Accounts (1 to 2)
                    if row.get('bank 1 account no'):
                        profile.bank_accounts.all().delete()
                        for i in range(1, 3):
                            acc_no = str(row.get(f'bank {i} account no', '')).strip()
                            if acc_no:
                                ifsc = str(row.get(f'bank {i} ifsc', '')).strip()
                                b_type = get_choice_key(row.get(f'bank {i} type'), BankAccount.ACCOUNT_TYPES) or 'SB'
                                b_name = str(row.get(f'bank {i} name', ''))
                                is_def = parse_bool(row.get(f'bank {i} default (y/n)'))

                                BankAccount.objects.create(
                                    investor=profile,
                                    account_number=acc_no,
                                    ifsc_code=ifsc,
                                    account_type=b_type,
                                    bank_name=b_name,
                                    is_default=is_def
                                )

                    count += 1

            except Exception as e:
                errors.append(f"Row {row_idx}: {str(e)}")

    except Exception as e:
        errors.append(f"File Error: {str(e)}")

    return count, errors


def import_distributors_from_file(file_obj):
    """
    Parses a CSV/Excel file with Distributor Details.
    Supports comprehensive field set with Upsert logic.
    """
    count = 0
    errors = []

    try:
        rows = read_file_to_dicts(file_obj, DISTRIBUTOR_COLUMN_MAP)

        # Validate Required Columns
        if rows and 'arn' not in rows[0]:
            return 0, ["Critical Error: 'ARN' column not found in file. Supported headers: ARN, ARN Number, Distributor ARN, ARN Code."]

        for row_idx, row in enumerate(rows, start=1):
            try:
                arn = str(row.get('arn', '')).strip().upper()
                name = str(row.get('name', '')).strip()
                email = str(row.get('email', '')).strip()
                mobile = str(row.get('mobile', '')).strip()
                pan = str(row.get('pan', '')).strip().upper()
                euin = str(row.get('euin', '')).strip().upper()
                broker_code = str(row.get('broker code', row.get('sub broker code', ''))).strip()

                # Optional Hierarchy
                parent_arn = str(row.get('parent arn (optional)', '')).strip().upper()
                rm_code = str(row.get('rm employee code (optional)', '')).strip()

                with transaction.atomic():
                    # Check/Create User
                    user = None
                    try:
                        user = User.objects.get(username=broker_code)
                        # Upsert User Details
                        if name: user.name = name
                        if email: user.email = email
                        user.save()
                    except User.DoesNotExist:
                        user = User.objects.create_user(username=broker_code, email=email, password=pan, force_password_change=True)
                        user.name = name
                        user.user_type = User.Types.DISTRIBUTOR
                        user.save()

                    # Check/Create Profile
                    profile, created = DistributorProfile.objects.get_or_create(user=user,broker_code=broker_code, defaults={'pan': pan, 'mobile': mobile, 'euin': euin, 'arn_number': arn})

                    if pan: profile.pan = pan
                    if mobile: profile.mobile = mobile
                    if euin: profile.euin = euin

                    # Address Details
                    if row.get('address'): profile.address = row.get('address')
                    if row.get('city'): profile.city = row.get('city')
                    if row.get('state'): profile.state = row.get('state') # Assuming state value matches or we might need normalization if it's strict choices
                    if row.get('pincode'): profile.pincode = row.get('pincode')
                    if row.get('country'): profile.country = row.get('country')

                    # Contact Details
                    if row.get('alternate mobile'): profile.alternate_mobile = row.get('alternate mobile')
                    if row.get('alternate email'): profile.alternate_email = row.get('alternate email')

                    # Personal/Business Details
                    dob = parse_date(row.get('date of birth') or row.get('dob'))
                    if dob: profile.dob = dob
                    if row.get('gstin'): profile.gstin = row.get('gstin')

                    # Bank Details
                    if row.get('bank name'): profile.bank_name = row.get('bank name')
                    if row.get('account number'): profile.account_number = row.get('account number')
                    if row.get('ifsc code'): profile.ifsc_code = row.get('ifsc code')
                    if row.get('account type'): profile.account_type = get_choice_key(row.get('account type'), DistributorProfile.ACCOUNT_TYPES)
                    if row.get('branch name'): profile.branch_name = row.get('branch name')

                    # Hierarchy Linking
                    if parent_arn:
                        try:
                            parent = DistributorProfile.objects.get(arn_number=parent_arn)
                            profile.parent = parent
                        except DistributorProfile.DoesNotExist:
                            pass # Or log warning

                    if rm_code:
                        try:
                            rm = RMProfile.objects.get(employee_code=rm_code)
                            profile.rm = rm
                        except RMProfile.DoesNotExist:
                            pass

                    profile.save()
                    count += 1

            except Exception as e:
                errors.append(f"Row {row_idx}: {str(e)}")

    except Exception as e:
        errors.append(f"File Error: {str(e)}")

    return count, errors

def import_rms_from_file(file_obj):
    """
    Parses a CSV/Excel file with RM Details.
    Uses Employee Code as unique identifier.
    Requires Branch Code for linking.
    """
    count = 0
    errors = []

    try:
        rows = read_file_to_dicts(file_obj, RM_COLUMN_MAP)

        # Validate Required Columns
        if rows and 'employee code' not in rows[0]:
             return 0, ["Critical Error: 'Employee Code' column not found in file. Supported headers: Employee Code, Emp Code, RM Code."]

        for row_idx, row in enumerate(rows, start=1):
            try:
                emp_code = str(row.get('employee code', '')).strip()
                if not emp_code:
                    continue

                name = str(row.get('name', '')).strip()
                email = str(row.get('email', '')).strip()
                branch_code = str(row.get('branch code', '')).strip()

                # Validate Branch
                branch = None
                if branch_code:
                    try:
                        branch = Branch.objects.get(code=branch_code)
                    except Branch.DoesNotExist:
                        raise ValueError(f"Branch with code '{branch_code}' not found.")
                else:
                    # Decide if branch is mandatory. Requirement says "link the RM to an existing Branch".
                    # If branch code is missing, maybe allowed? But if provided and wrong, fail.
                    # Let's assume mandatory for now or at least if provided must exist.
                    # If empty, we can proceed without branch.
                    pass

                with transaction.atomic():
                    # Check/Create User
                    user = None
                    try:
                        user = User.objects.get(username=emp_code)
                        # Upsert
                        if name: user.name = name
                        if email: user.email = email
                        user.save()
                    except User.DoesNotExist:
                        user = User.objects.create_user(username=emp_code, email=email, password=emp_code, force_password_change=True)
                        user.name = name
                        user.user_type = User.Types.RM
                        user.save()

                    # Check/Create Profile
                    profile, created = RMProfile.objects.get_or_create(user=user, defaults={'employee_code': emp_code})

                    if branch:
                        profile.branch = branch

                    # Address Details
                    if row.get('address'): profile.address = row.get('address')
                    if row.get('city'): profile.city = row.get('city')
                    if row.get('state'): profile.state = row.get('state')
                    if row.get('pincode'): profile.pincode = row.get('pincode')
                    if row.get('country'): profile.country = row.get('country')

                    # Contact Details
                    if row.get('alternate mobile'): profile.alternate_mobile = row.get('alternate mobile')
                    if row.get('alternate email'): profile.alternate_email = row.get('alternate email')

                    # Personal/Business
                    dob = parse_date(row.get('date of birth') or row.get('dob'))
                    if dob: profile.dob = dob
                    if row.get('gstin'): profile.gstin = row.get('gstin')

                    # Bank Details
                    if row.get('bank name'): profile.bank_name = row.get('bank name')
                    if row.get('account number'): profile.account_number = row.get('account number')
                    if row.get('ifsc code'): profile.ifsc_code = row.get('ifsc code')
                    if row.get('account type'): profile.account_type = get_choice_key(row.get('account type'), RMProfile.ACCOUNT_TYPES)
                    if row.get('branch name'): profile.branch_name = row.get('branch name')

                    if 'active status (y/n)' in row:
                        profile.is_active = parse_bool(row.get('active status (y/n)'))
                        user.is_active = profile.is_active
                        user.save()

                    profile.save()
                    count += 1

            except Exception as e:
                errors.append(f"Row {row_idx}: {str(e)}")

    except Exception as e:
        errors.append(f"File Error: {str(e)}")

    return count, errors
