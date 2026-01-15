from apps.users.models import InvestorProfile, BankAccount, Nominee

def map_state_to_code(state_name):
    """
    Maps state names to BSE State Codes.
    Defaults to 'MA' (Maharashtra) or 'XX' (Others) if not found.
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
    return mapping.get(normalized, 'XX')

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
    # Safe access to name field if it exists, else fallback to first+last
    user_name = getattr(investor.user, 'name', '')
    full_name = user_name if user_name else (investor.user.first_name + " " + investor.user.last_name)
    first_name, middle_name, last_name = split_name(full_name)

    # 0-8: Basic Details (Indices 0-8)
    f0_8 = [
        client_code,
        first_name, middle_name, last_name,
        investor.tax_status,
        investor.gender,
        date_fmt(investor.dob),
        investor.occupation,
        investor.holding_nature
    ]

    # 9-20: Second/Third Holder Details (Indices 9-20)
    # Fields:
    # 9: 2nd First Name
    # 10: 2nd Middle
    # 11: 2nd Last
    # 12: 3rd First
    # 13: 3rd Middle
    # 14: 3rd Last
    # 15: 2nd DOB
    # 16: 3rd DOB
    # 17: Guardian First (if Minor)
    # 18: Guardian Middle (if Minor)
    # 19: Guardian Last (if Minor)
    # 20: Guardian DOB

    sec_first, sec_middle, sec_last = split_name(investor.second_applicant_name)
    thd_first, thd_middle, thd_last = split_name(investor.third_applicant_name)
    g_first, g_middle, g_last = split_name(investor.guardian_name)

    f9_20 = [
        sec_first, sec_middle, sec_last,
        thd_first, thd_middle, thd_last,
        date_fmt(investor.second_applicant_dob),
        date_fmt(investor.third_applicant_dob),
        g_first, g_middle, g_last,
        "" # Guardian DOB not stored in InvestorProfile currently (only name/pan), so sending blank or need to add field? Assuming blank for now as it wasn't requested explicitly beyond "details".
    ]

    # 21: Guardian Exempt / Holder 1 Exempt Flag (Sample 'N')
    # If Primary PAN is Exempt, Y, else N. Currently defaulting to N unless we check PAN format.
    # Assuming 'N' as per previous implementation unless we have exempt flag field.
    # We do have specific exempt flags added now? No, we added them to model? No, I added them.
    # Wait, did I add PAN Exempt flags? No, I added Joint Holder DOBs.
    # Let's check model update again. I did not add PAN Exempt flags. I'll stick to 'N' default or infer.
    f21 = ["N"]

    # 22-24: Exempt Flags for 2nd, 3rd, Guardian
    f22_24 = ["N", "N", "N"]

    # 25-28: PANs (P, S, T, G)
    g_pan = investor.guardian_pan if investor.tax_status == InvestorProfile.MINOR else ""
    f25_28 = [
        investor.pan,
        investor.second_applicant_pan,
        investor.third_applicant_pan,
        g_pan
    ]

    # 29-32: Exempt Categories (Empty for now)
    f29_32 = ["", "", "", ""]

    # 33: Client Type (P=Physical, D=Demat)
    f33 = [investor.client_type]

    # 34-39: Demat Details (6 Fields)
    if investor.client_type == InvestorProfile.DEMAT:
        dep = investor.depository
        dp_id = investor.dp_id
        cl_id = investor.client_id
        f34_39 = [dep, dp_id, cl_id, "", "", ""]
    else:
        f34_39 = [""] * 6

    # 40-44: Bank 1 Details (Fields 41-45)
    # Sorted by ID (creation order) but prioritize default.
    all_banks = list(investor.bank_accounts.all())
    # Sort: Default first, then others
    all_banks.sort(key=lambda b: not b.is_default)

    # Pad to 5 banks
    banks = all_banks[:5]
    while len(banks) < 5:
        banks.append(None)

    # Bank 1
    b1 = banks[0]
    f40_44 = [
        b1.account_type if b1 else "SB",
        b1.account_number if b1 else "",
        "", # MICR
        b1.ifsc_code.strip() if b1 and b1.ifsc_code else "",
        "Y" if b1 else "N" # Default Flag
    ]

    # 45-64: Banks 2-5 (4 banks * 5 fields = 20 fields)
    f45_64 = []
    for i in range(1, 5):
        bk = banks[i]
        f45_64.extend([
            bk.account_type if bk else "",
            bk.account_number if bk else "",
            "", # MICR
            bk.ifsc_code.strip() if bk and bk.ifsc_code else "",
            "N" # Not default
        ])

    # 65-66: Cheque Name & Div Pay Mode
    f65_66 = [full_name, "01"] # 01=Payout

    # 67-73: Address (Fields 68-74)
    state_code = map_state_to_code(investor.state)
    f67_73 = [
        investor.address_1,
        investor.address_2,
        investor.address_3,
        investor.city,
        state_code,
        investor.pincode,
        investor.country
    ]

    # 74-77: Contact (Resi/Off Phone/Fax) - Using Mobile for Resi Phone as fallback
    f74_77 = [investor.mobile, "", "", ""]

    # 78: Email
    email_to_use = investor.email if investor.email else investor.user.email
    f78 = [email_to_use]

    # 79: Comm Mode (P=Physical, M=Mobile, E=Electronic)
    f79 = ["M"] # Use Mobile/Email as preferred

    # 80-90: Foreign Address (11 Fields) (Indices 80-90)
    # Fields: Add1, Add2, Add3, City, Pin, State, Country, ResPhone, ResFax, OffPhone, OffFax
    f_state_code = map_state_to_code(investor.foreign_state)
    f80_90 = [
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

    # 91: Mobile
    f91 = [investor.mobile]

    # 92: KYC Type (K=KYC Compliant)
    f92 = ["K"]

    # 93-99: Other KYC Types (7 Empty)
    f93_99 = [""] * 7

    # 100-103: KRA Exempt Refs (4 Empty)
    f100_103 = [""] * 4

    # 104-105: Aadhaar/Mapin
    f104_105 = ["", investor.mapin_id]

    # 106: Paperless Flag
    f106 = [investor.paperless_flag]

    # 107-108: LEI
    f107_108 = [investor.lei_no, date_fmt(investor.lei_validity)]

    # 109-110: Mobile/Email Declaration (SE=Self)
    f109_110 = ["SE", "SE"]

    # 111-119: Reserved/Empty (9 Fields)
    f111_119 = [""] * 9

    # --- Nominee Section ---
    nominees = list(investor.nominees.all())

    # 120: Nominee Opted (Y/N)
    f120 = ["Y"] if nominees else ["N"]

    # 121: Nominee Reg Type / SOA Flag
    f121 = ["O"] if nominees else ["N"]

    # Helper for Relation Code Mapping
    def get_rel_code(rel_name):
        r = rel_name.lower()
        if 'spouse' in r or 'wife' in r or 'husband' in r: return '01'
        if 'father' in r: return '07'
        if 'mother' in r: return '08'
        if 'son' in r: return '11'
        if 'daughter' in r: return '12'
        return '15' # Others

    nom_blocks = []
    # Loop for 3 possible nominees
    for i in range(3):
        if i < len(nominees):
            n = nominees[i]

            # Fields
            nm_name = n.name
            nm_rel = get_rel_code(n.relationship)
            # Format percentage (e.g., 100.00 -> 100)
            nm_perc = str(int(n.percentage)) if n.percentage % 1 == 0 else str(n.percentage)
            nm_minor = "Y" if n.guardian_name else "N"
            nm_dob = date_fmt(n.date_of_birth)
            nm_g_name = n.guardian_name
            nm_g_pan = n.guardian_pan
            nm_alloc = str(i + 1)
            nm_pan = n.pan if n.pan else ""

            # Use Nominee specific Address/Contact
            nm_email = n.email
            nm_mobile = n.mobile
            nm_addr1 = n.address_1
            nm_addr2 = n.address_2
            nm_addr3 = n.address_3
            nm_city = n.city
            nm_state = map_state_to_code(n.state)
            nm_pin = n.pincode

            block = [
                nm_name, nm_rel, nm_perc, nm_minor, nm_dob,
                nm_g_name, nm_g_pan, nm_alloc, nm_pan,
                nm_addr1, nm_addr2, nm_addr3, nm_city, nm_state, nm_pin,
                "", # Telephone
                nm_mobile, nm_email
            ]
        else:
            block = [""] * 18

        nom_blocks.extend(block)

    # 173: Declaration Flag
    f173 = ["Y"]

    # 174-182: Empty (6 Fields for now, check exact count)
    # Total fields check:
    # 0-8: 9
    # 9-20: 12
    # 21: 1
    # 22-24: 3
    # 25-28: 4
    # 29-32: 4
    # 33: 1
    # 34-39: 6
    # 40-44: 5
    # 45-64: 20
    # 65-66: 2
    # 67-73: 7
    # 74-77: 4
    # 78: 1
    # 79: 1
    # 80-90: 11
    # 91: 1
    # 92: 1
    # 93-99: 7
    # 100-103: 4
    # 104-105: 2
    # 106: 1
    # 107-108: 2
    # 109-110: 2
    # 111-119: 9
    # 120: 1
    # 121: 1
    # 122-139 (Nom1): 18
    # 140-157 (Nom2): 18
    # 158-175 (Nom3): 18
    # 176 (Dec Flag): 1
    # Total so far: 9+12+1+3+4+4+1+6+5+20+2+7+4+1+1+11+1+1+7+4+2+1+2+2+9+1+1+18+18+18+1 = 176
    # 183 - 176 = 7 fields remaining.

    # Wait, my previous index calculation had 173 as Dec Flag.
    # Start of Nominee Block is after Index 121.
    # Nom1: 122..139
    # Nom2: 140..157
    # Nom3: 158..175
    # Next Index is 176.
    # So f176 is "Y".
    # Remaining indices: 177, 178, 179, 180, 181, 182. (6 fields).
    # So f177_182 = [""] * 6.

    f176 = ["Y"]
    f177_182 = [""] * 6

    # Combine all
    all_fields = (
        f0_8 + f9_20 + f21 + f22_24 + f25_28 + f29_32 + f33 + f34_39 +
        f40_44 + f45_64 + f65_66 + f67_73 + f74_77 + f78 + f79 +
        f80_90 + f91 + f92 + f93_99 + f100_103 + f104_105 + f106 +
        f107_108 + f109_110 + f111_119 + f120 + f121 + nom_blocks +
        f176 + f177_182
    )

    return "|".join([str(f) for f in all_fields])


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

    buy_sell = order.transaction_type
    if buy_sell == 'SIP':
        buy_sell = 'P'

    buy_sell_type = "FRESH" if order.is_new_folio else "ADDITIONAL"
    client_code = order.investor.ucc_code if order.investor.ucc_code else order.investor.pan

    euin = order.euin if order.euin else ""
    euin_flag = "Y" if euin else "N"
    folio_no = order.folio.folio_number if order.folio else ""
    dpc = "N"
    trans_mode = "P"

    txt_amount = f"{order.amount:.2f}" if order.amount else "0"
    txt_quantity = f"{order.units:.4f}" if order.units else "0"

    params = {
        'TransactionCode': 'NEW',
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
        'KYCStatus': 'Y',
        'SubMemberCode': '',
        'Password': password,
        'PassKey': pass_key,
        'Param1': '',
        'Param2': '',
        'Param3': ''
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

    folio_no = sip.folio.folio_number if sip.folio else ""
    buy_sell_type = "FRESH" if not folio_no else "ADDITIONAL"

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
        'UserId': user_id,
        'TransMode': 'P',
        'DPC': 'N',
        'MandateID': sip.mandate.mandate_id,
        'FirstOrderFlag': 'Y',
        'Brokerage': '',
        'FrequencyType': freq_map.get(sip.frequency, 'MONTHLY'),
        'StartDate': start_date,
        'InstallmentAmount': f"{sip.amount:.2f}",
        'NoOfInstallment': str(sip.installments),
        'EUIN': euin,
        'EuinFlag': 'Y' if euin else 'N',
        'SubBrCode': '',
        'FolioNo': folio_no,
        'BuySellType': buy_sell_type,
        'Remarks': '',
        'SubMemberCode': '',
        'Password': password,
        'PassKey': pass_key,
        'Param1': '',
        'Param2': '',
        'Param3': ''
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
        'UserId': user_id,
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
