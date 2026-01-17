import re
from apps.users.models import InvestorProfile

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
            if not n.relationship:
                errors.append(f"Nominee {i} ({n.name}): Relationship is missing.")

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
