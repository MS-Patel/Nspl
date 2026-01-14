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

    # 1. Client Code (UCC)
    client_code = investor.ucc_code if investor.ucc_code else investor.pan

    # Name splitting
    # Safe access to name field if it exists, else fallback to first+last
    user_name = getattr(investor.user, 'name', '')
    full_name = user_name if user_name else (investor.user.first_name + " " + investor.user.last_name)
    parts = full_name.split()
    first_name = parts[0] if parts else ""
    last_name = parts[-1] if len(parts) > 1 else ""
    middle_name = " ".join(parts[1:-1]) if len(parts) > 2 else ""

    # 0-8: Basic Details
    f0_8 = [
        client_code,
        first_name, middle_name, last_name,
        investor.tax_status,
        investor.gender,
        date_fmt(investor.dob),
        investor.occupation,
        investor.holding_nature
    ]

    # 9-20: Second/Third Holder Details (12 Empty Fields)
    # Note: If we supported joint holders, we would fill this. Currently supporting Single.
    f9_20 = [""] * 12

    # 21: Guardian Exempt / Holder 1 Exempt Flag? (Sample has 'N')
    f21 = ["N"]

    # 22-24: Exempt Flags for 2nd, 3rd, Guardian (Empty)
    f22_24 = ["", "", ""]

    # 25-28: PANs (P, S, T, G)
    # If Minor, Guardian PAN is required.
    g_pan = investor.guardian_pan if investor.tax_status == InvestorProfile.MINOR else ""
    f25_28 = [investor.pan, "", "", g_pan]

    # 29-32: Exempt Categories (Empty)
    f29_32 = ["", "", "", ""]

    # 33: Client Type (P=Physical, D=Demat)
    f33 = [investor.client_type]

    # 34-39: Demat Details (6 Fields: 35-40)
    # Corrected alignment: Fields 35, 36, 37, 38, 39, 40.
    if investor.client_type == InvestorProfile.DEMAT:
        dep = investor.depository
        dp_id = investor.dp_id
        cl_id = investor.client_id

        f34_39 = [dep, dp_id, cl_id, "", "", ""]
    else:
        f34_39 = [""] * 6

    # 40-44: Bank 1 Details (Fields 41-45)
    # 41: Acc Type (Index 40)
    # 42: Acc No (Index 41)
    # 43: MICR (Index 42) - Empty
    # 44: IFSC (Index 43)
    # 45: Default Bank Flag (Index 44) - "Y"

    bank = investor.bank_accounts.filter(is_default=True).first()
    if not bank:
        bank = investor.bank_accounts.first()

    acc_type = bank.account_type if bank else "SB"
    acc_no = bank.account_number if bank else ""
    ifsc = bank.ifsc_code.strip() if bank and bank.ifsc_code else ""

    f40_44 = [acc_type, acc_no, "", ifsc, "Y"]

    # 45-64: Banks 2-5 (20 Empty Fields) - Fields 46-65
    f45_64 = [""] * 20

    # 65-66: Cheque Name & Div Pay Mode (Fields 66-67)
    f65_66 = [full_name, "01"] # 01=Payout? Sample had 01.

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

    # 74-77: Contact (Resi/Off Phone/Fax) - Empty (Fields 75-78)
    f74_77 = ["", "", "", ""]

    # 78: Email (Field 79)
    email_to_use = investor.email if investor.email else investor.user.email
    f78 = [email_to_use]

    # 79: Comm Mode (P=Physical, M=Mobile, E=Electronic) (Field 80)
    # Sample uses P.
    f79 = ["P"]

    # 80-90: Foreign Address (11 Empty Fields) (Fields 81-91)
    f80_90 = [""] * 11

    # 91: Mobile (Field 92)
    f91 = [investor.mobile]

    # 92: KYC Type (K=KYC Compliant?) - Sample 'K' (Field 93)
    f92 = ["K"]

    # 93-99: Other KYC Types (7 Empty) (Fields 94-100)
    f93_99 = [""] * 7

    # 100-103: KRA Exempt Refs (4 Empty) (Fields 101-104)
    f100_103 = [""] * 4

    # 104-105: Aadhaar/Mapin (Empty) (Fields 105-106)
    f104_105 = ["", ""]

    # 106: Paperless Flag (Sample P) (Field 107)
    f106 = ["P"]

    # 107-108: LEI (Empty) (Fields 108-109)
    f107_108 = ["", ""]

    # 109-110: Mobile/Email Declaration (SE=Self) (Fields 110-111)
    f109_110 = ["SE", "SE"]

    # 111-119: Reserved/Empty (9 Fields) (Fields 112-120)
    f111_119 = [""] * 9

    # --- Nominee Section ---
    nominees = list(investor.nominees.all())

    # 120: Nominee Opted (Y/N) (Field 121)
    f120 = ["Y"] if nominees else ["N"]

    # 121: Nominee Reg Type / SOA Flag (Field 122)
    # If no nominees, this must be "N" (Nominee SOA Flag mentioned as N error)
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

            # Use Investor Contact/Addr as fallback
            nm_email = investor.email if investor.email else investor.user.email
            nm_mobile = investor.mobile
            nm_addr1 = investor.address_1
            nm_addr2 = investor.address_2
            nm_addr3 = investor.address_3
            nm_city = investor.city
            nm_pin = investor.pincode
            nm_country = investor.country

            block = [
                nm_name, nm_rel, nm_perc, nm_minor, nm_dob,
                nm_g_name, nm_g_pan, nm_alloc, nm_pan,
                nm_email, nm_mobile,
                nm_addr1, nm_addr2, nm_addr3, nm_city, nm_pin, nm_country
            ]
        else:
            block = [""] * 17

        nom_blocks.extend(block)

    # 173: Declaration Flag? (Sample Y) (Field 174)
    # Previously mapped as f174
    f173 = ["Y"]

    # 174-182: Empty (9 Fields) (Fields 175-183)
    # Adjusted to ensure total 183 fields.
    f174_182 = [""] * 9

    # Combine all
    all_fields = (
        f0_8 + f9_20 + f21 + f22_24 + f25_28 + f29_32 + f33 + f34_39 +
        f40_44 + f45_64 + f65_66 + f67_73 + f74_77 + f78 + f79 +
        f80_90 + f91 + f92 + f93_99 + f100_103 + f104_105 + f106 +
        f107_108 + f109_110 + f111_119 + f120 + f121 + nom_blocks +
        f173 + f174_182
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
