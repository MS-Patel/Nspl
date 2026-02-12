import csv
import logging
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.users.models import InvestorProfile, DistributorProfile, RMProfile

User = get_user_model()
logger = logging.getLogger(__name__)

def import_investors_from_file(file_obj):
    """
    Parses a CSV file with Investor Details.
    Expected Columns: PAN, Firstname, Middlename, Lastname, Email, Mobile
    """
    count = 0
    errors = []

    try:
        decoded_file = file_obj.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)

        # Normalize headers
        reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]

        for row_idx, row in enumerate(reader, start=1):
            try:
                pan = row.get('pan', '').strip().upper()
                firstname = row.get('firstname', '').strip()
                middlename = row.get('middlename', '').strip()
                lastname = row.get('lastname', '').strip()

                # Construct full name
                full_name = f"{firstname} {middlename} {lastname}".replace('  ', ' ').strip()

                email = row.get('email', '').strip()
                mobile = row.get('mobile', '').strip()

                if not pan:
                    errors.append(f"Row {row_idx}: Missing PAN")
                    continue

                with transaction.atomic():
                    # Check/Create User
                    user = None
                    try:
                        user = User.objects.get(username=pan)
                    except User.DoesNotExist:
                        user = User.objects.create_user(username=pan, email=email, password=pan)
                        user.name = full_name
                        user.user_type = User.Types.INVESTOR
                        user.save()

                    # Check/Create Profile
                    profile, created = InvestorProfile.objects.get_or_create(user=user, defaults={'pan': pan})

                    # Update details
                    updated = False
                    if full_name and user.name != full_name:
                        user.name = full_name
                        user.save()

                    if firstname and profile.firstname != firstname:
                        profile.firstname = firstname
                        updated = True
                    if middlename and profile.middlename != middlename:
                        profile.middlename = middlename
                        updated = True
                    if lastname and profile.lastname != lastname:
                        profile.lastname = lastname
                        updated = True

                    if email and profile.email != email:
                        profile.email = email
                        updated = True
                    if mobile and profile.mobile != mobile:
                        profile.mobile = mobile
                        updated = True

                    if updated:
                        profile.save()

                    if created or updated:
                        count += 1

            except Exception as e:
                errors.append(f"Row {row_idx}: {str(e)}")

    except Exception as e:
        errors.append(f"File Error: {str(e)}")

    return count, errors


def import_distributors_from_file(file_obj):
    """
    Parses a CSV file with Distributor Details.
    Expected Columns: ARN, Name, Email, Mobile, PAN
    """
    count = 0
    errors = []

    try:
        decoded_file = file_obj.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)

        reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]

        for row_idx, row in enumerate(reader, start=1):
            try:
                arn = row.get('arn', '').strip().upper() # ARN-XXXX
                name = row.get('name', '').strip()
                email = row.get('email', '').strip()
                mobile = row.get('mobile', '').strip()
                pan = row.get('pan', '').strip().upper()

                if not arn:
                    errors.append(f"Row {row_idx}: Missing ARN")
                    continue

                # Ensure ARN format? Let's be lenient for now, but usually starts with ARN-

                with transaction.atomic():
                    # Check/Create User (Username = ARN)
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

                    updated = False
                    if pan and profile.pan != pan:
                        profile.pan = pan
                        updated = True
                    if mobile and profile.mobile != mobile:
                        profile.mobile = mobile
                        updated = True

                    if updated:
                        profile.save()

                    if created or updated:
                        count += 1

            except Exception as e:
                errors.append(f"Row {row_idx}: {str(e)}")

    except Exception as e:
        errors.append(f"File Error: {str(e)}")

    return count, errors
