from apps.users.models import InvestorProfile, BankAccount, Nominee

def map_state_to_code(state_name):
    """
    Maps state names to BSE State Codes.
    Defaults to 'MA' (Maharashtra) or 'XX' (Others) if not found.
    This is a basic mapping, ideally should be a ChoiceField in the model.
    """
    mapping = {
        'ANDAMAN & NICOBAR': 'AN', 'ANDHRA PRADESH': 'AP', 'ARUNACHAL PRADESH': 'AR',
        'ASSAM': 'AS', 'BIHAR': 'BH', 'CHANDIGARH': 'CH', 'CHHATTISGARH': 'CG',
        'DADRA AND NAGAR HAVELI': 'DN', 'DAMAN AND DIU': 'DD', 'DELHI': 'DL',
        'GOA': 'GO', 'GUJARAT': 'GU', 'HARYANA': 'HA', 'HIMACHAL PRADESH': 'HP',
        'JAMMU & KASHMIR': 'JM', 'JHARKHAND': 'JK', 'KARNATAKA': 'KA', 'KERALA': 'KE',
        'LAKSHADWEEP': 'LD', 'MADHYA PRADESH': 'MP', 'MAHARASHTRA': 'MA', 'MANIPUR': 'MN',
        'MEGHALAYA': 'ME', 'MIZORAM': 'MI', 'NAGALAND': 'NA', 'NEW DELHI': 'ND',
        'ODISHA': 'OR', 'ORISSA': 'OR', 'PUDUCHERRY': 'PO', 'PONDICHERRY': 'PO',
        'PUNJAB': 'PU', 'RAJASTHAN': 'RA', 'SIKKIM': 'SI', 'TAMIL NADU': 'TN',
        'TELANGANA': 'TG', 'TRIPURA': 'TR', 'UTTAR PRADESH': 'UP', 'UTTARAKHAND': 'UC',
        'UTTARANCHAL': 'UC', 'WEST BENGAL': 'WB'
    }

    if not state_name:
        return ""

    normalized = state_name.strip().upper()
    return mapping.get(normalized, 'XX') # Default to Others if not found

def map_investor_to_bse_param_string(investor):
    """
    Maps an InvestorProfile object to the pipe-separated string required by BSE Enhanced UCC Registration.

    Format (based on MFI/MFD New Common Client Registration Parameter Structure):
    Client Code | First Name | Middle Name | Last Name | Tax Status | Gender | DOB | Occupation |
    Holding Nature | Second Holder First Name | ... (many fields)
    """

    # Helper to get value or empty string
    def val(v):
        return str(v) if v else ""

    # Helper for dates (DD/MM/YYYY)
    def date_fmt(d):
        return d.strftime("%d/%m/%Y") if d else ""

    # 1. Client Code (UCC)
    client_code = investor.ucc_code if investor.ucc_code else investor.pan

    # Name splitting (Naive assumption: First Last or First Middle Last)
    full_name = investor.user.first_name + " " + investor.user.last_name
    parts = full_name.split()
    first_name = parts[0] if parts else ""
    last_name = parts[-1] if len(parts) > 1 else ""
    middle_name = " ".join(parts[1:-1]) if len(parts) > 2 else ""

    # Primary Holder Info
    p_first_name = first_name
    p_middle_name = middle_name
    p_last_name = last_name

    tax_status = investor.tax_status
    gender = investor.gender
    dob = date_fmt(investor.dob)
    occupation = investor.occupation
    holding = investor.holding_nature

    # Second/Third Holder (Not implemented in model yet, sending blank)
    sec_h_fname = ""
    sec_h_mname = ""
    sec_h_lname = ""
    thd_h_fname = ""
    thd_h_mname = ""
    thd_h_lname = ""
    sec_h_dob = ""
    thd_h_dob = ""

    # Guardian (Only if Minor)
    guardian_fname = ""
    guardian_mname = ""
    guardian_lname = ""
    guardian_dob = ""

    if tax_status == InvestorProfile.MINOR:
        # Split guardian name
        g_parts = investor.guardian_name.split()
        guardian_fname = g_parts[0] if g_parts else ""
        guardian_lname = g_parts[-1] if len(g_parts) > 1 else ""
        guardian_mname = " ".join(g_parts[1:-1]) if len(g_parts) > 2 else ""

    # PAN Exempt Flags
    p_pan_exempt = "N"
    s_pan_exempt = "N"
    t_pan_exempt = "N"
    g_pan_exempt = "N"

    # PANs
    p_pan = investor.pan
    s_pan = investor.second_applicant_pan
    t_pan = investor.third_applicant_pan
    g_pan = investor.guardian_pan

    # Exempt Categories (Blank if Exempt is N)
    p_exempt_cat = ""
    s_exempt_cat = ""
    t_exempt_cat = ""
    g_exempt_cat = ""

    # Client Type (P=Physical)
    client_type = "P"

    # Demat Details
    pms_code = ""
    default_dp = ""
    cdsl_dp_id = ""
    cdsl_clt_id = ""
    cmbp_id = ""
    nsdl_dp_id = ""
    nsdl_clt_id = ""

    # Bank Details
    bank = investor.bank_accounts.filter(is_default=True).first()
    if not bank:
        bank = investor.bank_accounts.first()

    acc_type_1 = bank.account_type if bank else "SB"
    acc_no_1 = bank.account_number if bank else ""
    micr_1 = ""
    ifsc_1 = bank.ifsc_code if bank else ""
    default_bank_flag_1 = "Y"

    # Other banks (2-5) - sending blank

    # Cheque Name
    cheque_name = full_name

    # Div Pay Mode
    div_pay_mode = "02"

    # Address
    addr1 = investor.address_1
    addr2 = investor.address_2
    addr3 = investor.address_3
    city = investor.city
    state_code = map_state_to_code(investor.state)
    pincode = investor.pincode
    country = investor.country

    # Contact
    resi_phone = ""
    resi_fax = ""
    off_phone = ""
    off_fax = ""
    email = investor.email
    comm_mode = "M" # Mobile

    # Foreign Addr (For NRI)
    f_addr1 = ""
    f_addr2 = ""
    f_addr3 = ""
    f_city = ""
    f_pin = ""
    f_state = ""
    f_country = ""
    f_resi = ""
    f_fax = ""
    f_off = ""
    f_off_fax = ""

    indian_mobile = investor.mobile

    # Nominees
    nominee = investor.nominees.first()
    n1_name = nominee.name if nominee else ""
    n1_rel = nominee.relationship if nominee else ""
    n1_perc = str(nominee.percentage) if nominee else ""
    n1_minor_flag = "N"
    n1_dob = ""
    n1_guardian = nominee.guardian_name if nominee else ""

    # Nominees 2 & 3 (Blank)

    # KYC Details
    p_kyc_type = "K"
    p_ckyc = ""
    s_kyc_type = ""
    s_ckyc = ""
    t_kyc_type = ""
    t_ckyc = ""
    g_kyc_type = ""
    g_ckyc = ""

    # KRA Exempt Ref No
    p_kra_ex_ref = ""
    s_kra_ex_ref = ""
    t_kra_ex_ref = ""
    g_kra_ex_ref = ""

    # Misc
    aadhaar_updated = "N"
    mapin_id = ""
    paperless_flag = "Z" # Z=Paperless
    lei_no = ""
    lei_validity = ""

    mobile_decl_flag = "SE" # Self
    email_decl_flag = "SE" # Self

    # Construct the list of values
    fields = [
        client_code,
        p_first_name, p_middle_name, p_last_name,
        tax_status, gender, dob, occupation, holding,
        sec_h_fname, sec_h_mname, sec_h_lname,
        thd_h_fname, thd_h_mname, thd_h_lname,
        sec_h_dob, thd_h_dob,
        guardian_fname, guardian_mname, guardian_lname, guardian_dob,
        p_pan_exempt, s_pan_exempt, t_pan_exempt, g_pan_exempt,
        p_pan, s_pan, t_pan, g_pan,
        p_exempt_cat, s_exempt_cat, t_exempt_cat, g_exempt_cat,
        client_type,
        pms_code, default_dp, cdsl_dp_id, cdsl_clt_id, cmbp_id, nsdl_dp_id, nsdl_clt_id,
        acc_type_1, acc_no_1, micr_1, ifsc_1, default_bank_flag_1,
        "", "", "", "", "", # Bank 2
        "", "", "", "", "", # Bank 3
        "", "", "", "", "", # Bank 4
        "", "", "", "", "", # Bank 5
        cheque_name, div_pay_mode,
        addr1, addr2, addr3, city, state_code, pincode, country,
        resi_phone, resi_fax, off_phone, off_fax, email,
        comm_mode,
        f_addr1, f_addr2, f_addr3, f_city, f_pin, f_state, f_country,
        f_resi, f_fax, f_off, f_off_fax,
        indian_mobile,
        n1_name, n1_rel, n1_perc, n1_minor_flag, n1_dob, n1_guardian,
        "", "", "", "", "", "", # Nominee 2
        "", "", "", "", "", "", # Nominee 3
        p_kyc_type, p_ckyc,
        s_kyc_type, s_ckyc,
        t_kyc_type, t_ckyc,
        g_kyc_type, g_ckyc,
        p_kra_ex_ref, s_kra_ex_ref, t_kra_ex_ref, g_kra_ex_ref,
        aadhaar_updated, mapin_id, paperless_flag,
        lei_no, lei_validity,
        mobile_decl_flag, email_decl_flag
    ]

    # Join with pipe
    return "|".join([str(f) for f in fields])


def get_bse_order_params(order, member_id, user_id, password, pass_key):
    """
    Constructs the parameter dictionary for BSE StarMF orderEntryParam API (SOAP).

    Args:
        order (Order): The order object.
        member_id (str): BSE Member ID.
        user_id (str): BSE User ID.
        password (str): Encrypted Session Password.
        pass_key (str): Random Pass Key used for encryption.

    Returns:
        dict: Parameters to be passed to client.service.orderEntryParam()
    """

    # Map Order fields to BSE fields

    # 1. Transaction Code & BuySell
    # Order.PURCHASE ('P') -> BuySell 'P'
    # Order.REDEMPTION ('R') -> BuySell 'R'
    # Order.SWITCH ('S') -> BuySell 'S'
    # Order.SIP ('SIP') -> Handled separately usually, but for Lumpsum API it might be 'P' with SIP flag or separate API.
    # Current task is Lumpsum.

    buy_sell = order.transaction_type
    if buy_sell == 'SIP':
        # Default to P for now if it gets here, but SIP usually uses different logic
        buy_sell = 'P'

    # 2. BuySellType (FRESH vs ADDITIONAL)
    buy_sell_type = "FRESH" if order.is_new_folio else "ADDITIONAL"

    # 3. Client Code
    client_code = order.investor.ucc_code if order.investor.ucc_code else order.investor.pan

    # 4. EUIN
    euin = order.euin if order.euin else ""
    euin_flag = "Y" if euin else "N"

    # 5. Folio
    folio_no = order.folio.folio_number if order.folio else ""

    # 6. DPC (Depository Participant Charge) - Physical is usually 'N'
    dpc = "N"

    # 7. Transaction Mode - Physical 'P', Demat 'D'
    trans_mode = "P"

    # 8. Amount & Units
    # Format amount to 2 decimal places usually required, or simple string.
    txt_amount = f"{order.amount:.2f}" if order.amount else "0"
    # Format quantity to 4 decimal places (standard for MF units)
    txt_quantity = f"{order.units:.4f}" if order.units else "0"

    if buy_sell == 'R' or buy_sell == 'S':
        # For Redemption/Switch, amount might be 0 if units are specified
        # But our order model has both.
        pass

    # Construct the dictionary based on standard orderEntryParam signature
    params = {
        'TransactionCode': 'NEW', # Always NEW for entry
        'UniqueRefNo': str(order.unique_ref_no),
        'SchemeCode': order.scheme.scheme_code,
        'MemberCode': member_id,
        'ClientCode': client_code,
        'UserId': user_id,
        'BuySell': buy_sell,
        'BuySellType': buy_sell_type,
        'DPC': dpc,
        'TransMode': trans_mode,
        'TxtAmount': txt_amount,
        'TxtQuantity': txt_quantity,
        'MandateId': order.mandate.mandate_id if order.mandate else "",
        'EUIN': euin,
        'SubBrCode': '',
        'EuinFlag': euin_flag,
        'MinRedeem': 'N',
        'DematFlag': 'N',
        'AllRedeem': 'N',
        'FolioNo': folio_no,
        'Remarks': '',
        'KYCStatus': 'Y', # Assuming compliant
        'SubMemberCode': '',
        'Password': password,
        'PassKey': pass_key,
        'Param1': '',
        'Param2': '',
        'Param3': ''
    }

    return params
