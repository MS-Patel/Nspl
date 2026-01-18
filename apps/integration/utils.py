from apps.users.models import InvestorProfile, BankAccount, Nominee
from apps.users.constants import STATE_MAPPING

def map_state_to_code(state_name):
    """
    Maps state names to BSE State Codes.
    Defaults to 'MA' (Maharashtra) or 'XX' (Others) if not found.
    """
    if not state_name:
        return ""

    normalized = state_name.strip().upper()
    return STATE_MAPPING.get(normalized, 'XX')

def get_rel_code(rel_name):
    """
    Maps relationship names to BSE Relationship Codes based on V183 specs.
    01 - AUNT, 02 - BROTHER-IN-LAW, 03 - BROTHER, 04 - DAUGHTER, 05 - DAUGHTER-IN-LAW,
    06 - FATHER, 07 - FATHER-IN-LAW, 08 - GRAND DAUGHTER, 09 - GRAND FATHER,
    10 - GRAND MOTHER, 11 - GRAND SON, 12 - MOTHER-IN-LAW, 13 - MOTHER,
    14 - NEPHEW, 15 - NIECE, 16 - SISTER, 17 - SISTER-IN-LAW, 18 - SON,
    19 - SON-IN-LAW, 20 - SPOUSE, 21 - UNCLE, 22 - OTHERS, 23 - COURT APPOINTED LEGAL GUARDIAN
    """
    if not rel_name:
        return "22" # Default to Others if empty but required

    r = rel_name.strip().upper()

    # Exact map for all standard choices provided
    mapping = {
        'AUNT': '01',
        'BROTHER-IN-LAW': '02',
        'BROTHER': '03',
        'DAUGHTER': '04',
        'DAUGHTER-IN-LAW': '05',
        'FATHER': '06',
        'FATHER-IN-LAW': '07',
        'GRAND DAUGHTER': '08',
        'GRAND FATHER': '09',
        'GRAND MOTHER': '10',
        'GRAND SON': '11',
        'MOTHER-IN-LAW': '12',
        'MOTHER': '13',
        'NEPHEW': '14',
        'NIECE': '15',
        'SISTER': '16',
        'SISTER-IN-LAW': '17',
        'SON': '18',
        'SON-IN-LAW': '19',
        'SPOUSE': '20',
        'UNCLE': '21',
        'OTHERS': '22',
        'COURT APPOINTED LEGAL GUARDIAN': '23'
    }

    # Direct lookup
    if r in mapping:
        return mapping[r]

    # Heuristic Fallbacks (Handling variations)
    if 'WIFE' in r or 'HUSBAND' in r: return '20'

    return '22' # Fallback to Others

def get_nominee_id_details(id_type_code, id_number):
    """
    Maps internal Nominee ID Type codes to BSE V183 integer codes and formats the ID number.
    BSE Codes:
    1 - PAN (10 chars)
    2 - Aadhaar (Last 4 digits)
    3 - Driving License (Max 20)
    4 - Passport (Max 9)
    """
    if not id_type_code:
        return "", ""

    # Internal codes (from apps.users.models.Nominee.ID_TYPE_CHOICES)
    # 'A': Passport -> 4
    # 'C': PAN Card -> 1
    # 'D': ID Card -> Others? Not in strict list 1-4.
    # 'E': Driving License -> 3
    # 'G': UIDIA / Aadhar letter -> 2

    bse_type = ""
    bse_number = str(id_number).strip() if id_number else ""

    if id_type_code == 'C': # PAN
        bse_type = "1"
        # Ensure alphanumeric? BSE validation will handle, but we pass as is.
    elif id_type_code == 'G': # Aadhaar
        bse_type = "2"
        # Last 4 digits only
        if len(bse_number) > 4:
            bse_number = bse_number[-4:]
    elif id_type_code == 'E': # Driving License
        bse_type = "3"
    elif id_type_code == 'A': # Passport
        bse_type = "4"
    else:
        # If type is not one of 1,2,3,4, what to do?
        # The user said "Nominee 1 identity type must be 1, 2, 3 or 4".
        # We will attempt to map 'B' (Voter ID) or others if possible, or just default to something safe?
        # Since strict validation is on, sending an invalid code like 'B' or empty might fail.
        # However, for now we map what we know. If unknown, we send what we have and let it fail or be empty if strictly required.
        # But if we return empty type, BSE might complain if Opted=Y.
        pass

    return bse_type, bse_number

def map_investor_to_bse_param_string(investor):
    """
    Maps an InvestorProfile object to the pipe-separated string required by BSE Enhanced UCC Registration V183.
    Total Fields: 183
    """

    # Helper to get value or empty string
    def val(v):
        return str(v) if v else ""

    # Helper for dates (DD/MM/YYYY)
    def date_fmt(d):
        return d.strftime("%d/%m/%Y") if d else ""

    # Helper to split name
    def split_name(full_name):
        if not full_name: return "", "", ""
        parts = full_name.strip().split()
        first = parts[0]
        last = parts[-1] if len(parts) > 1 else ""
        middle = " ".join(parts[1:-1]) if len(parts) > 2 else ""
        return first, middle, last

    # 1. Client Code (UCC)
    client_code = investor.ucc_code if investor.ucc_code else investor.pan

    # Name splitting
    user_name = getattr(investor.user, 'name', '')
    full_name = user_name if user_name else (investor.user.first_name + " " + investor.user.last_name)
    first_name, middle_name, last_name = split_name(full_name)

    # 1-9: Basic Details
    f01_09 = [
        client_code,                        # 1: Client Code (UCC)
        first_name,                         # 2: Primary Holder First Name
        middle_name,                        # 3: Primary Holder Middle Name
        last_name,                          # 4: Primary Holder Last Name
        investor.tax_status,                # 5: Tax Status
        investor.gender,                    # 6: Gender
        date_fmt(investor.dob),             # 7: Primary Holder DOB/Incorporation
        investor.occupation,                # 8: Occupation Code
        investor.holding_nature             # 9: Holding Nature
    ]

    # 10-21: Joint Holders & Guardian
    sec_first, sec_middle, sec_last = split_name(investor.second_applicant_name)
    thd_first, thd_middle, thd_last = split_name(investor.third_applicant_name)
    g_first, g_middle, g_last = split_name(investor.guardian_name)

    f10_21 = [
        sec_first, sec_middle, sec_last,    # 10-12: Second Holder Name
        thd_first, thd_middle, thd_last,    # 13-15: Third Holder Name
        date_fmt(investor.second_applicant_dob), # 16: Second Holder DOB
        date_fmt(investor.third_applicant_dob),  # 17: Third Holder DOB
        g_first, g_middle, g_last,          # 18-20: Guardian Name
        ""                                  # 21: Guardian DOB
    ]

    # 22-25: PAN Exempt Flags
    # Spec: Mandatory in Case of Joint Holding/Anyone or Survivor, and if Second Holder name mentioned
    f22_25 = [
        "N", # 22: Primary Exempt
        "N" if investor.second_applicant_name else "", # 23: Second Exempt
        "N" if investor.third_applicant_name else "", # 24: Third Exempt
        "N" if investor.guardian_name else ""  # 25: Guardian Exempt
    ]

    # 26-29: PANs
    f26_29 = [
        investor.pan,                       # 26
        investor.second_applicant_pan,      # 27
        investor.third_applicant_pan,       # 28
        investor.guardian_pan               # 29
    ]

    # 30-33: Exempt Categories
    f30_33 = ["", "", "", ""]               # 30, 31, 32, 33

    # 34: Client Type
    f34 = [investor.client_type]            # 34

    # 35: PMS (Optional)
    f35 = [""]                              # 35

    # 36-41: Demat Details
    dep = ""
    cdsl_dp = ""
    cdsl_cl = ""
    cmbp = ""
    nsdl_dp = ""
    nsdl_cl = ""

    if investor.client_type == InvestorProfile.DEMAT:
        if investor.depository == 'C': # CDSL
            dep = "CDSL"
            cdsl_dp = investor.dp_id
            cdsl_cl = investor.client_id
        elif investor.depository == 'N': # NSDL
            dep = "NSDL"
            nsdl_dp = investor.dp_id
            nsdl_cl = investor.client_id

    f36_41 = [dep, cdsl_dp, cdsl_cl, cmbp, nsdl_dp, nsdl_cl] # 36-41

    # 42-66: Bank Accounts (5 Banks x 5 Fields)
    all_banks = list(investor.bank_accounts.all())
    all_banks.sort(key=lambda b: not b.is_default) # Default first

    bank_fields = []
    for i in range(5):
        if i < len(all_banks):
            b = all_banks[i]
            bank_fields.extend([
                b.account_type,                     # Acc Type
                b.account_number,                   # Acc No
                "",                                 # MICR
                b.ifsc_code.strip(),                # IFSC
                "Y" if i == 0 else "N"              # Default Flag (Only 1st is Y)
            ])
        else:
            # Spec: Default Bank Flag 2 SHOULD BE BLANK, IF ACC TYPE BLANK
            bank_fields.extend(["", "", "", "", ""]) # Empty bank block

    f42_66 = bank_fields

    # 67: Cheque Name
    f67 = [full_name]

    # 68: Div Pay Mode
    div_mode = "04" if (all_banks and all_banks[0].ifsc_code) else "01"
    f68 = [div_mode]

    # 69-75: Address Details
    state_code = map_state_to_code(investor.state)
    f69_75 = [
        investor.address_1,
        investor.address_2,
        investor.address_3,
        investor.city,
        state_code,
        investor.pincode,
        investor.country
    ]

    # 76-79: Contact
    f76_79 = [
        "",                     # 76: Resi Phone
        "",                     # 77: Resi Fax
        "",                     # 78: Off Phone
        ""                      # 79: Off Fax
    ]

    # 80: Email
    email_to_use = investor.email if investor.email else investor.user.email
    f80 = [email_to_use]

    # 81: Comm Mode (P/E/M)
    f81 = ["M"]

    # 82-92: Foreign Address
    f_state_code = map_state_to_code(investor.foreign_state)
    f82_92 = [
        investor.foreign_address_1,
        investor.foreign_address_2,
        investor.foreign_address_3,
        investor.foreign_city,
        investor.foreign_pincode,
        f_state_code,
        investor.foreign_country,
        investor.foreign_resi_phone,
        investor.foreign_res_fax,
        investor.foreign_off_phone,
        investor.foreign_off_fax
    ]

    # 93: Indian Mobile
    f93 = [investor.mobile]

    # 94-123: KYC, CKYC, KRA Exempt, Contact, Dec, Guardian Rel, Nom Opt, Auth Mode
    # Aligned with V183 structure where detailed Nominee block starts at 124.

    # 94-101: KYC/CKYC
    f94_101 = [
        investor.kyc_type,                      # 94: Prim KYC Type
        investor.ckyc_number,                   # 95: Prim CKYC
        investor.second_applicant_kyc_type,     # 96: Sec KYC Type
        investor.second_applicant_ckyc_number,  # 97: Sec CKYC
        investor.third_applicant_kyc_type,      # 98: Thd KYC Type
        investor.third_applicant_ckyc_number,   # 99: Thd CKYC
        investor.guardian_kyc_type,             # 100: Guard KYC Type
        investor.guardian_ckyc_number           # 101: Guard CKYC
    ]

    # 102-105: KRA Exempt Ref
    f102_105 = [
        investor.kra_exempt_ref_no,                 # 102
        investor.second_applicant_kra_exempt_ref_no,# 103
        investor.third_applicant_kra_exempt_ref_no, # 104
        investor.guardian_kra_exempt_ref_no         # 105
    ]

    # 106-110: Misc
    f106_110 = [
        "",                                     # 106: Aadhaar Updated
        investor.mapin_id,                      # 107: Mapin ID
        investor.paperless_flag,                # 108: Paperless Flag
        investor.lei_no,                        # 109: LEI
        date_fmt(investor.lei_validity)         # 110: LEI Validity
    ]

    # 111-120: Contact Declarations
    # Spec: CANT ENTER DECLARATION FLAG IF MOBILE NUMBER IS NOT MENTIONED (applies to Email too)
    f111_120 = [
        investor.mobile_declaration if investor.mobile else "",            # 111: Prim Mob Dec
        investor.email_declaration if email_to_use else "",             # 112: Prim Email Dec
        investor.second_applicant_email,        # 113: Sec Email
        investor.second_applicant_email_declaration if investor.second_applicant_email else "", # 114: Sec Email Dec
        investor.second_applicant_mobile,       # 115: Sec Mobile
        investor.second_applicant_mobile_declaration if investor.second_applicant_mobile else "", # 116: Sec Mob Dec
        investor.third_applicant_email,         # 117: Thd Email
        investor.third_applicant_email_declaration if investor.third_applicant_email else "",   # 118: Thd Email Dec
        investor.third_applicant_mobile,        # 119: Thd Mobile
        investor.third_applicant_mobile_declaration if investor.third_applicant_mobile else ""   # 120: Thd Mob Dec
    ]

    # 121-123: Guardian Rel, Nom Opt, Auth Mode
    # Handle 'P' -> 'W' mapping for legacy 'Physical' values
    auth_mode = investor.nomination_auth_mode
    if auth_mode == 'P':
        auth_mode = 'W'

    f121_123 = [
        investor.guardian_relationship,         # 121
        investor.nomination_opt,                # 122
        auth_mode                               # 123
    ]

    # 124-174: Detailed Nominee Blocks (3 x 17 fields)
    nominees = list(investor.nominees.all())
    f_nom_detailed = []

    for i in range(3):
        if i < len(nominees):
            n = nominees[i]
            minor_flag = "Y" if n.guardian_name else "N"
            perc = str(int(n.percentage)) if n.percentage % 1 == 0 else str(n.percentage)

            bse_id_type, bse_id_number = get_nominee_id_details(n.id_type, n.id_number)

            f_nom_detailed.extend([
                n.name,                     # 124 Name
                get_rel_code(n.relationship), # 125 Relationship (using code)
                perc,                       # 126 %
                minor_flag,                 # 127 Minor
                date_fmt(n.date_of_birth) if minor_flag == "Y" else "",  # 128 DOB (Only if minor)
                n.guardian_name,            # 129 Guardian
                n.guardian_pan,             # 130 Guardian PAN
                bse_id_type,                # 131 ID Type
                bse_id_number,              # 132 ID No
                n.email,                    # 133 Email
                n.mobile,                   # 134 Mobile
                n.address_1,                # 135 Addr 1
                n.address_2,                # 136 Addr 2
                n.address_3,                # 137 Addr 3
                n.city,                     # 138 City
                n.pincode,                  # 139 Pin
                n.country                   # 140 Country
            ])
        else:
            f_nom_detailed.extend([""] * 17)

    # 175: Nominee SOA Flag
    f175 = ["N"]

    # 176-183: Fillers
    f176_183 = [""] * 8

    all_fields = (
        f01_09 + f10_21 + f22_25 + f26_29 + f30_33 + f34 + f35 + f36_41 +
        f42_66 + f67 + f68 + f69_75 + f76_79 + f80 + f81 + f82_92 + f93 +
        f94_101 + f102_105 + f106_110 + f111_120 + f121_123 +
        f_nom_detailed + f175 + f176_183
    )

    return "|".join([str(f) for f in all_fields])


def get_bse_order_params(order, member_id, user_id, password, pass_key):
    """
    Constructs the parameter dictionary for BSE StarMF orderEntryParam API (SOAP).
    Corrected to match WSDL signature found in error logs.
    """

    buy_sell = order.transaction_type
    if buy_sell == 'SIP':
        buy_sell = 'P'

    buy_sell_type = "FRESH" if order.is_new_folio else "ADDITIONAL"
    client_code = order.investor.ucc_code if order.investor.ucc_code else order.investor.pan

    euin = order.euin if order.euin else ""
    euin_flag = "Y" if euin else "N"
    folio_no = order.folio.folio_number if order.folio else ""
    dpc = "N"

    # User confirmed TransMode P -> DPTxn
    dptxn = "P" # Physical

    txt_amount = f"{order.amount:.2f}" if order.amount else "0"
    txt_quantity = f"{order.units:.4f}" if order.units else "0"

    # Mobile and Email from Investor
    mobile_no = order.investor.mobile if order.investor.mobile else ""
    # Use email from investor profile or user account
    email_id = order.investor.email if order.investor.email else order.investor.user.email

    params = {
        'TransCode': 'NEW',
        'TransNo': str(order.unique_ref_no),
        'OrderId': '', # Optional/Empty
        'UserID': user_id,
        'MemberId': member_id,
        'ClientCode': client_code,
        'SchemeCd': order.scheme.scheme_code,
        'BuySell': buy_sell,
        'BuySellType': buy_sell_type,
        'DPTxn': dptxn,
        'OrderVal': txt_amount,
        'Qty': txt_quantity,
        'AllRedeem': 'N',
        'FolioNo': folio_no,
        'Remarks': '',
        'KYCStatus': 'Y',
        'RefNo': '', # Optional
        'SubBrCode': '',
        'EUIN': euin,
        'EUINVal': euin_flag,
        'MinRedeem': 'N',
        'DPC': dpc,
        'IPAdd': '', # Optional
        'Password': password,
        'PassKey': pass_key,
        'Parma1': '', # Note typo match
        'Param2': '',
        'Param3': '',
        'MobileNo': mobile_no,
        'EmailID': email_id,
        'MandateID': order.mandate.mandate_id if order.mandate else "",
        'Filler1': '',
        'Filler2': '',
        'Filler3': '',
        'Filler4': '',
        'Filler5': '',
        'Filler6': ''
    }

    return params

def get_bse_xsip_order_params(sip, member_id, user_id, password, pass_key):
    """
    Constructs the parameter dictionary for BSE StarMF xsipOrderEntryParam API (SOAP).
    """

    client_code = sip.investor.ucc_code if sip.investor.ucc_code else sip.investor.pan

    euin = ""
    if sip.investor.distributor:
        euin = sip.investor.distributor.euin

    # Standard EUIN Flag Logic
    euin_val = "Y" if euin else "N"

    folio_no = sip.folio.folio_number if sip.folio else ""

    # Logic for BuySellType usually not in XSIP but FirstOrderFlag is there
    # However, Postman XML doesn't show BuySellType for XSIP. It shows FirstOrderFlag.

    freq_map = {
        'MONTHLY': 'MONTHLY',
        'WEEKLY': 'WEEKLY',
        'QUARTERLY': 'QUARTERLY'
    }

    start_date = sip.start_date.strftime("%d/%m/%Y")

    params = {
        'TransactionCode': 'NEW',
        'UniqueRefNo': f"SIP-{sip.id}",
        'SchemeCode': sip.scheme.scheme_code,
        'MemberCode': member_id,
        'ClientCode': client_code,
        'UserID': user_id, # Updated Case
        'InternalRefNo': '',
        'TransMode': 'P',
        'DpTxnMode': 'P', # Assuming Physical like DPTxn
        'StartDate': start_date,
        'FrequencyType': freq_map.get(sip.frequency, 'MONTHLY'),
        'FrequencyAllowed': '', # Optional
        'InstallmentAmount': f"{sip.amount:.2f}",
        'NoOfInstallment': str(sip.installments),
        'Remarks': '',
        'FolioNo': folio_no,
        'FirstOrderFlag': 'Y',
        'Brokerage': '',
        'MandateID': sip.mandate.mandate_id,
        'SubberCode': '', # Updated Name
        'Euin': euin,
        'EuinVal': euin_val, # Updated Name
        'DPC': 'N',
        'XsipRegID': '', # Postman uses XsipRegID
        'IPAdd': '',
        'Password': password,
        'PassKey': pass_key,
        'Param1': '',
        'Param2': '',
        'Param3': '',
        'Filler1': '',
        'Filler2': '',
        'Filler3': '',
        'Filler4': '',
        'Filler5': '',
        'Filler6': ''
    }

    return params

def get_bse_mandate_params(mandate, member_id, user_id, password, pass_key):
    """
    Constructs parameters for mandateRegistrationParam (XSIP Mandate).
    """
    client_code = mandate.investor.ucc_code if mandate.investor.ucc_code else mandate.investor.pan

    bank = mandate.bank_account
    if not bank:
        bank = mandate.investor.bank_accounts.filter(is_default=True).first()

    params = {
        'MemberCode': member_id,
        'ClientCode': client_code,
        'UserId': user_id, # Check Case: Postman usually matches OrderEntry so maybe UserID?
                           # But WSDL for mandate is distinct. Keeping UserId as per existing code unless error seen.
                           # Actually, standardizing on UserID is safer given OrderEntry but Mandate often has legacy UserId.
                           # I will stick to UserId for now as I don't have a WSDL log for Mandate error.
                           # Wait, I should probably match the pattern if I can.
                           # Let's check if I can find Mandate example.
                           # Postman collection doesn't show Mandate WSDL.
                           # I'll update it to be safe if I can, but without proof, better leave it or make it robust.
                           # Current code had UserId.
        'MandateType': 'XSIP',
        'MandateAmount': f"{mandate.amount_limit:.2f}",
        'StartDate': mandate.start_date.strftime("%d/%m/%Y"),
        'EndDate': mandate.end_date.strftime("%d/%m/%Y") if mandate.end_date else "31/12/2099",
        'BankAccountNo': bank.account_number if bank else "",
        'IFSC': bank.ifsc_code if bank else "",
        'BankName': bank.bank_name if bank else "",
        'AccountType': bank.account_type if bank else "SB",
        'Password': password,
        'PassKey': pass_key,
        'Param1': '',
        'Param2': '',
        'Param3': ''
    }
    return params
