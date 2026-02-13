import csv
import logging
import pandas as pd
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.users.models import InvestorProfile, DistributorProfile, RMProfile, BankAccount, Nominee
from datetime import datetime

User = get_user_model()
logger = logging.getLogger(__name__)

def read_file_to_dicts(file_obj):
    """
    Reads a CSV or Excel file and returns a list of dictionaries.
    Keys are normalized (lowercase, stripped).
    """
    data = []
    filename = file_obj.name.lower()

    try:
        if filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file_obj)
            # Replace NaN with empty string
            df = df.fillna('')
            # Convert to list of dicts
            records = df.to_dict('records')
            # Normalize keys
            data = [{str(k).strip().lower(): v for k, v in row.items()} for row in records]
        else:
            # Assume CSV
            decoded_file = file_obj.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
            data = list(reader)
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

def import_investors_from_file(file_obj):
    """
    Parses a CSV/Excel file with Investor Details.
    Supports extended fields including Bank Accounts and Nominees.
    """
    count = 0
    errors = []

    try:
        rows = read_file_to_dicts(file_obj)

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
                    except User.DoesNotExist:
                        user = User.objects.create_user(username=pan, email=email, password=pan)
                        user.name = full_name
                        user.user_type = User.Types.INVESTOR
                        user.save()

                    # 2. Investor Profile
                    profile, created = InvestorProfile.objects.get_or_create(user=user, defaults={'pan': pan})

                    # Update fields
                    profile.firstname = firstname
                    profile.middlename = middlename
                    profile.lastname = lastname
                    profile.email = email
                    profile.mobile = mobile

                    # Map extended fields
                    profile.tax_status = get_choice_key(row.get('tax status'), InvestorProfile.TAX_STATUS_CHOICES) or InvestorProfile.INDIVIDUAL
                    profile.occupation = get_choice_key(row.get('occupation'), InvestorProfile.OCCUPATION_CHOICES) or InvestorProfile.SERVICE
                    profile.holding_nature = get_choice_key(row.get('holding nature'), InvestorProfile.HOLDING_CHOICES) or InvestorProfile.SINGLE
                    profile.source_of_wealth = get_choice_key(row.get('source of wealth'), InvestorProfile.SOURCE_OF_WEALTH_CHOICES) or InvestorProfile.SALARY
                    profile.income_slab = get_choice_key(row.get('income slab'), InvestorProfile.INCOME_SLAB_CHOICES) or InvestorProfile.ONE_TO_5L
                    profile.pep_status = get_choice_key(row.get('pep status'), InvestorProfile.PEP_CHOICES) or InvestorProfile.PEP_NO

                    profile.place_of_birth = row.get('place of birth', 'India')
                    profile.country_of_birth = row.get('country of birth', 'India')
                    profile.exemption_code = get_choice_key(row.get('exemption code'), InvestorProfile.EXEMPTION_CODE_CHOICES)

                    # Date of Birth
                    dob_val = row.get('date of birth (yyyy-mm-dd)') or row.get('dob')
                    if dob_val:
                        try:
                            if isinstance(dob_val, datetime):
                                profile.dob = dob_val.date()
                            else:
                                profile.dob = pd.to_datetime(dob_val).date()
                        except:
                            pass # Keep existing or None

                    gender_val = str(row.get('gender', '')).upper()
                    if gender_val.startswith('M'): profile.gender = 'M'
                    elif gender_val.startswith('F'): profile.gender = 'F'
                    elif gender_val.startswith('O'): profile.gender = 'O'

                    # Address
                    profile.address_1 = str(row.get('address 1', ''))[:40]
                    profile.address_2 = str(row.get('address 2', ''))[:40]
                    profile.address_3 = str(row.get('address 3', ''))[:40]
                    profile.city = str(row.get('city', ''))[:35]
                    profile.state = str(row.get('state', ''))[:30]
                    profile.pincode = str(row.get('pincode', ''))[:6]
                    profile.country = str(row.get('country', 'India'))[:35]

                    # Foreign Address
                    profile.foreign_address_1 = str(row.get('foreign address 1', ''))[:40]
                    profile.foreign_address_2 = str(row.get('foreign address 2', ''))[:40]
                    profile.foreign_address_3 = str(row.get('foreign address 3', ''))[:40]
                    profile.foreign_city = str(row.get('foreign city', ''))[:35]
                    profile.foreign_state = str(row.get('foreign state', ''))[:35]
                    profile.foreign_pincode = str(row.get('foreign pincode', ''))[:10]
                    profile.foreign_country = str(row.get('foreign country', ''))[:35]

                    # Demat
                    profile.client_type = get_choice_key(row.get('client type'), InvestorProfile.CLIENT_TYPE_CHOICES) or InvestorProfile.PHYSICAL
                    profile.depository = get_choice_key(row.get('depository'), InvestorProfile.DEPOSITORY_CHOICES)
                    profile.dp_id = str(row.get('dp id', ''))
                    profile.client_id = str(row.get('client id', ''))

                    # Other
                    profile.ucc_code = str(row.get('ucc code', '')).strip()
                    profile.is_offline = parse_bool(row.get('is offline (y/n)'))

                    profile.save()

                    # 3. Nominees (1 to 3)
                    # Clear existing? Or append? Clearing is safer for "Import" which implies overwrite state
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
                            n_dob_val = row.get(f'nominee {i} dob')
                            n_dob = None
                            if n_dob_val:
                                try:
                                    if isinstance(n_dob_val, datetime):
                                        n_dob = n_dob_val.date()
                                    else:
                                        n_dob = pd.to_datetime(n_dob_val).date()
                                except: pass

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
    """
    count = 0
    errors = []

    try:
        rows = read_file_to_dicts(file_obj)

        for row_idx, row in enumerate(rows, start=1):
            try:
                arn = str(row.get('arn', '')).strip().upper()
                if not arn:
                    continue

                name = str(row.get('name', '')).strip()
                email = str(row.get('email', '')).strip()
                mobile = str(row.get('mobile', '')).strip()
                pan = str(row.get('pan', '')).strip().upper()
                euin = str(row.get('euin', '')).strip().upper()

                # Optional Hierarchy
                parent_arn = str(row.get('parent arn (optional)', '')).strip().upper()
                rm_code = str(row.get('rm employee code (optional)', '')).strip()

                with transaction.atomic():
                    # Check/Create User
                    user = None
                    try:
                        user = User.objects.get(username=arn)
                    except User.DoesNotExist:
                        user = User.objects.create_user(username=arn, email=email, password=arn)
                        user.name = name
                        user.user_type = User.Types.DISTRIBUTOR
                        user.save()

                    # Check/Create Profile
                    profile, created = DistributorProfile.objects.get_or_create(user=user, defaults={'arn_number': arn})

                    profile.pan = pan
                    profile.mobile = mobile
                    profile.euin = euin

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
