import re
import csv
import io
from apps.users.models import InvestorProfile, BankAccount, User

def validate_investor_for_bse(investor: InvestorProfile) -> list[str]:
    """
    Validates an InvestorProfile against strict BSE requirements before API submission.
    Returns a list of error messages. If empty, validation passed.
    """
    errors = []

    # 1. Basic Fields
    if not investor.pan:
        errors.append("PAN is missing.")
    elif not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', investor.pan):
        errors.append(f"Invalid PAN format: {investor.pan}")

    if not investor.mobile:
        errors.append("Mobile number is missing.")
    elif not re.match(r'^[6-9]\d{9}$', investor.mobile):
        errors.append(f"Invalid Mobile number: {investor.mobile}")

    if not investor.email and not investor.user.email:
        errors.append("Email is missing.")

    # 2. Address Details
    if not investor.address_1:
        errors.append("Address Line 1 is missing.")
    if not investor.city:
        errors.append("City is missing.")
    if not investor.pincode:
        errors.append("Pincode is missing.")
    elif not re.match(r'^[1-9][0-9]{5}$', investor.pincode):
        errors.append(f"Invalid Pincode: {investor.pincode}")

    # NRI Check (Tax Status: 21, 24)
    if investor.tax_status in [InvestorProfile.NRI_REPATRIABLE, InvestorProfile.NRI_NON_REPATRIABLE]:
        if not investor.foreign_address_1:
            errors.append("Foreign Address Line 1 is missing for NRI Investor.")
        if not investor.foreign_city:
            errors.append("Foreign City is missing for NRI Investor.")
        if not investor.foreign_country:
            errors.append("Foreign Country is missing for NRI Investor.")
        if not investor.foreign_pincode:
            errors.append("Foreign Pincode is missing for NRI Investor.")

    # Demat Check
    if investor.client_type == InvestorProfile.DEMAT:
        if not investor.depository:
            errors.append("Depository (CDSL/NSDL) must be selected for Demat Client Type.")
        if investor.depository == InvestorProfile.CDSL:
            if not investor.dp_id: errors.append("DP ID is required for CDSL.")
            if not investor.client_id: errors.append("Client ID is required for CDSL.")
        elif investor.depository == InvestorProfile.NSDL:
            if not investor.dp_id: errors.append("DP ID is required for NSDL.")
            if not investor.client_id: errors.append("Client ID is required for NSDL.")


    # 3. Bank Account
    # Must have at least one account. We prioritize default, then first.
    bank = investor.bank_accounts.filter(is_default=True).first() or investor.bank_accounts.first()
    if not bank:
        errors.append("At least one Bank Account is required.")
    else:
        if not bank.account_number:
            errors.append("Bank Account Number is missing.")
        if not bank.ifsc_code:
            errors.append("IFSC Code is missing.")
        elif not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', bank.ifsc_code):
            errors.append(f"Invalid IFSC Code: {bank.ifsc_code}")

    # 4. Nominees
    # Check Nomination Opt
    if investor.nomination_opt == 'Y' and not investor.nomination_auth_mode:
        errors.append("Nomination Authentication Mode is mandatory when Nomination is Opted.")

    nominees = list(investor.nominees.all())
    if nominees:
        total_percentage = sum(n.percentage for n in nominees)
        if total_percentage != 100:
            errors.append(f"Total Nominee Percentage must be 100%. Current total: {total_percentage}%")

        for i, n in enumerate(nominees, 1):
            if not n.address_1:
                errors.append(f"Nominee {i} ({n.name}): Address Line 1 is missing.")
            if not n.city:
                errors.append(f"Nominee {i} ({n.name}): City is missing.")
            if not n.pincode:
                errors.append(f"Nominee {i} ({n.name}): Pincode is missing.")
            if not n.country:
                errors.append(f"Nominee {i} ({n.name}): Country is missing.")
            if not n.relationship:
                errors.append(f"Nominee {i} ({n.name}): Relationship is missing.")

            # BSE V183 Mandatory fields if Opted
            if investor.nomination_opt == 'Y':
                if not n.id_type:
                     errors.append(f"Nominee {i} ({n.name}): ID Type is mandatory.")
                if not n.id_number:
                     errors.append(f"Nominee {i} ({n.name}): ID Number is mandatory.")
                if not n.email:
                     errors.append(f"Nominee {i} ({n.name}): Email is mandatory.")
                if not n.mobile:
                     errors.append(f"Nominee {i} ({n.name}): Mobile is mandatory.")


            if n.date_of_birth:
                # Check for Minor
                from datetime import date
                today = date.today()
                # Calculate age
                age = today.year - n.date_of_birth.year - ((today.month, today.day) < (n.date_of_birth.month, n.date_of_birth.day))

                if age < 18:
                    if not n.guardian_name:
                        errors.append(f"Nominee {i} ({n.name}) is a minor but Guardian Name is missing.")
                    if not n.guardian_pan:
                        errors.append(f"Nominee {i} ({n.name}) is a minor but Guardian PAN is missing.")

    # 5. Minor Investor Check
    if investor.tax_status == InvestorProfile.MINOR:
        if not investor.guardian_name:
            errors.append("Investor is a Minor but Guardian Name is missing.")
        if not investor.guardian_pan:
            errors.append("Investor is a Minor but Guardian PAN is missing.")
        if not investor.guardian_relationship:
            errors.append("Investor is a Minor but Guardian Relationship is missing.")

    return errors

def process_client_master_csv(file):
    """
    Parses BSE Client Master CSV/Pipe file and updates InvestorProfiles.
    """
    decoded_file = file.read().decode('utf-8', errors='ignore')
    io_string = io.StringIO(decoded_file)

    # Detect delimiter
    import csv as csv_module
    sniffer = csv_module.Sniffer()
    try:
        # Check first few lines to determine format
        sample = decoded_file[:4096]
        dialect = sniffer.sniff(sample)
    except:
        # Fallback to excel (comma) if sniffing fails
        import csv
        dialect = csv.excel

    # Reset pointer
    io_string.seek(0)

    reader = csv.DictReader(io_string, dialect=dialect)

    updated_count = 0

    for row in reader:
        # Normalize keys (strip spaces, lowercase)
        clean_row = {k.strip().lower(): (v.strip() if v else '') for k, v in row.items() if k}

        # Find PAN key
        pan = clean_row.get('pan') or clean_row.get('pan no') or clean_row.get('pan_no')
        if not pan:
            continue

        # Find Profile
        try:
            profile = InvestorProfile.objects.get(pan=pan)
        except InvestorProfile.DoesNotExist:
             continue

        # Update Fields
        client_code = clean_row.get('clientcode') or clean_row.get('client code') or clean_row.get('client_code')
        if client_code:
            profile.ucc_code = client_code

        # Name
        name = clean_row.get('clientname') or clean_row.get('client name') or clean_row.get('investor name')
        if name:
             # Always update name from BSE Client Master as it is more authoritative than RTA provisional data
             profile.user.name = name
             profile.user.save()

        # Address
        addr1 = clean_row.get('address1') or clean_row.get('add1')
        if addr1: profile.address_1 = addr1

        addr2 = clean_row.get('address2') or clean_row.get('add2')
        if addr2: profile.address_2 = addr2

        addr3 = clean_row.get('address3') or clean_row.get('add3')
        if addr3: profile.address_3 = addr3

        city = clean_row.get('city')
        if city: profile.city = city

        pin = clean_row.get('pincode') or clean_row.get('pin')
        if pin: profile.pincode = pin

        state = clean_row.get('state')
        if state: profile.state = state

        email = clean_row.get('email') or clean_row.get('emailid')
        if email:
            if not profile.email:
                profile.email = email

            if not profile.user.email or "placeholder" in profile.user.email:
                profile.user.email = email
                profile.user.save()

        mobile = clean_row.get('mobile') or clean_row.get('mobileno')
        if mobile: profile.mobile = mobile

        # Bank Details
        acc_no = clean_row.get('accountno') or clean_row.get('bank account no') or clean_row.get('account_no') or clean_row.get('bank_account_no')
        if acc_no:
             ifsc = clean_row.get('ifsc') or clean_row.get('ifsc code') or clean_row.get('ifsc_code')
             bank_name = clean_row.get('bankname') or clean_row.get('bank name')

             # Check if bank exists
             bank_exists = profile.bank_accounts.filter(account_number=acc_no).exists()
             if not bank_exists:
                 BankAccount.objects.create(
                     investor=profile,
                     account_number=acc_no,
                     ifsc_code=ifsc if ifsc else 'UNKNOWN',
                     bank_name=bank_name if bank_name else '',
                     is_default=True
                 )

        # Mark as somewhat onboarded (at least has data)
        # Note: kyc_status logic depends on business rules.
        profile.save()
        updated_count += 1

    return updated_count
