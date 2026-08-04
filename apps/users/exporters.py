import csv
from decimal import Decimal
from pathlib import Path

from django.db.models import Prefetch

from apps.investments.models import Mandate, SIP
from apps.payouts.models import FolioDistributorMapping
from apps.users.models import BankAccount, DistributorProfile, InvestorProfile, Nominee, RMProfile


RM_HEADERS = [
    "name", "email", "mobile", "employee_code", "branch_code", "active", "city", "state",
    "pincode", "address", "pan", "alternate_mobile", "alternate_email", "dob", "gstin",
    "bank_name", "account_number", "ifsc_code", "branch_name", "country",
]

DISTRIBUTOR_HEADERS = [
    "name", "email", "mobile", "distributor_code", "branch_code", "rm_employee_code", "active",
    "is_approved", "arn_code", "subbroker_code", "euin_code", "city", "state", "pincode",
    "address", "pan", "alternate_mobile", "alternate_email", "dob", "gstin", "bank_name",
    "account_number", "ifsc_code", "branch_name", "country",
]

INVESTOR_CLIENT_MASTER_HEADERS = [
    "Member Code", "Client Code", "Primary Holder First Name", "Primary Holder Middle Name",
    "Primary Holder Last Name", "Tax Status", "Primary Holder DOB/Incorporation",
    "Occupation Code", "Holding Nature", "Primary Holder PAN", "Email", "Indian Mobile No.",
    "Address 1", "Address 2", "Address 3", "City", "State", "Pincode", "Country",
    "Second Holder First Name", "Second Holder Middle Name", "Second Holder Last Name",
    "Second Holder PAN", "Third Holder First Name", "Third Holder Middle Name",
    "Third Holder Last Name", "Third Holder PAN", "Guardian First Name",
    "Guardian Middle Name", "Guardian Last Name", "Guardian PAN", "Account No 1",
    "Bank Name 1", "Bank Branch 1", "IFSC Code 1", "Account Type 1", "Default Bank Flag 1",
    "Nominee 1 Name", "Nominee 1 %", "Nominee 1 Relationship", "Nominee 1 DOB",
    "Nominee 1 Guardian",
]

INVESTOR_FATCA_HEADERS = [
    "PAN_RP", "CO_BIR_INC", "PO_BIR_INC", "TAX_RES1", "OCC_CODE", "SRCE_WEALT",
    "INC_SLAB", "PEP_FLAG", "SrNo",
]

INVESTOR_MANDATE_HEADERS = [
    "MANDATE CODE", "CLIENT CODE", "BANK ACCOUNT NUMBER", "BANK NAME", "BANK BRANCH", "STATUS",
    "MANDATE TYPE", "AMOUNT", "START DATE", "END DATE", "REGN DATE", "APPROVED DATE",
    "UMRN NO", "REMARKS",
]

INVESTOR_SIP_HEADERS = [
    "SIP Registration Number", "PAN", "Client Code", "Scheme Code", "Mandate Code", "Amount",
    "Frequency", "Start Date", "End Date", "Installments", "Status", "Folio Number",
]

INVESTOR_RELATIONSHIP_HEADERS = [
    "investor_pan", "distributor_pan", "rm_code", "distributor_code",
]

FOLIO_DISTRIBUTOR_MAPPING_HEADERS = [
    "folio_number", "distributor_code",
]

ACCOUNT_TYPE_LABELS = {
    "SB": "SAVINGS",
    "CB": "CURRENT",
    "NE": "NRE",
    "NO": "NRO",
}

MANDATE_TYPE_LABELS = {
    Mandate.PHYSICAL: "XSP",
    Mandate.ISIP: "ISIP",
    Mandate.NET_BANKING: "NET_BANKING",
}

INCOME_SLAB_LABELS = {
    InvestorProfile.BELOW_1L: "Below-1L",
    InvestorProfile.ONE_TO_5L: "1-5L",
    InvestorProfile.FIVE_TO_10L: "5-10L",
    InvestorProfile.TEN_TO_25L: "10-25L",
    InvestorProfile.TWENTYFIVE_TO_1CR: "25L-1Cr",
    InvestorProfile.ABOVE_1CR: "Above-1Cr",
}


def export_new_portal_import_files(output_dir, member_code):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    investor_qs = InvestorProfile.objects.select_related(
        "user", "distributor", "rm", "branch"
    ).prefetch_related(
        Prefetch(
            "bank_accounts",
            queryset=BankAccount.objects.order_by("-is_default", "bse_index", "id"),
        ),
        Prefetch("nominees", queryset=Nominee.objects.order_by("id")),
    ).order_by("id")

    files = {
        "rm_bulk_import.csv": write_csv(
            output_path / "rm_bulk_import.csv",
            RM_HEADERS,
            build_rm_rows(),
        ),
        "distributor_bulk_import.csv": write_csv(
            output_path / "distributor_bulk_import.csv",
            DISTRIBUTOR_HEADERS,
            build_distributor_rows(),
        ),
        "investor_client-master.csv": write_csv(
            output_path / "investor_client-master.csv",
            INVESTOR_CLIENT_MASTER_HEADERS,
            build_investor_client_master_rows(investor_qs, member_code),
        ),
        "investor_fatca.csv": write_csv(
            output_path / "investor_fatca.csv",
            INVESTOR_FATCA_HEADERS,
            build_investor_fatca_rows(investor_qs),
        ),
        "investor_mandates.csv": write_csv(
            output_path / "investor_mandates.csv",
            INVESTOR_MANDATE_HEADERS,
            build_investor_mandate_rows(),
        ),
        "investor_sips.csv": write_csv(
            output_path / "investor_sips.csv",
            INVESTOR_SIP_HEADERS,
            build_investor_sip_rows(),
        ),
    }
    files.update(export_bbf_relationship_files(output_path))
    return files


def export_bbf_relationship_files(output_dir):
    """Export only the relationship files required for the BBF migration."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    return {
        "investor_relationships.csv": write_csv(
            output_path / "investor_relationships.csv",
            INVESTOR_RELATIONSHIP_HEADERS,
            build_investor_relationship_rows(),
        ),
        "folio_distributor_mappings.csv": write_csv(
            output_path / "folio_distributor_mappings.csv",
            FOLIO_DISTRIBUTOR_MAPPING_HEADERS,
            build_folio_distributor_mapping_rows(),
        ),
    }


def build_rm_rows():
    queryset = RMProfile.objects.select_related("user", "branch").order_by("id")
    return [
        {
            "name": profile.user.name or profile.user.get_full_name().strip() or profile.user.username,
            "email": profile.user.email,
            "mobile": profile.mobile,
            "employee_code": profile.employee_code,
            "branch_code": profile.branch.code if profile.branch else "",
            "active": yes_no(profile.is_active),
            "city": profile.city,
            "state": profile.state,
            "pincode": profile.pincode,
            "address": profile.address,
            "pan": profile.pan,
            "alternate_mobile": profile.alternate_mobile,
            "alternate_email": profile.alternate_email,
            "dob": format_date(profile.dob),
            "gstin": profile.gstin,
            "bank_name": profile.bank_name,
            "account_number": profile.account_number,
            "ifsc_code": profile.ifsc_code,
            "branch_name": profile.branch_name,
            "country": profile.country or "India",
        }
        for profile in queryset
    ]


def build_distributor_rows():
    queryset = DistributorProfile.objects.select_related("user", "rm__branch").order_by("id")
    return [
        {
            "name": profile.user.name or profile.user.get_full_name().strip() or profile.user.username,
            "email": profile.user.email,
            "mobile": profile.mobile,
            "distributor_code": profile.broker_code,
            "branch_code": profile.rm.branch.code if profile.rm and profile.rm.branch else "",
            "rm_employee_code": profile.rm.employee_code if profile.rm else "",
            "active": yes_no(profile.is_active),
            "is_approved": yes_no(profile.is_approved),
            "arn_code": profile.arn_number or "",
            "subbroker_code": profile.old_broker_code or "",
            "euin_code": profile.euin,
            "city": profile.city,
            "state": profile.state,
            "pincode": profile.pincode,
            "address": profile.address,
            "pan": profile.pan,
            "alternate_mobile": profile.alternate_mobile,
            "alternate_email": profile.alternate_email,
            "dob": format_date(profile.dob),
            "gstin": profile.gstin,
            "bank_name": profile.bank_name,
            "account_number": profile.account_number,
            "ifsc_code": profile.ifsc_code,
            "branch_name": profile.branch_name,
            "country": profile.country or "India",
        }
        for profile in queryset
    ]


def build_investor_client_master_rows(queryset, member_code):
    rows = []
    for investor in queryset:
        bank_account = first_or_none(investor.bank_accounts.all())
        nominee = first_or_none(investor.nominees.all())
        second_first, second_middle, second_last = split_name(investor.second_applicant_name)
        third_first, third_middle, third_last = split_name(investor.third_applicant_name)
        guardian_first, guardian_middle, guardian_last = split_name(investor.guardian_name)

        rows.append({
            "Member Code": member_code,
            "Client Code": client_code_for(investor),
            "Primary Holder First Name": investor.firstname,
            "Primary Holder Middle Name": investor.middlename,
            "Primary Holder Last Name": investor.lastname,
            "Tax Status": investor.get_tax_status_display().upper(),
            "Primary Holder DOB/Incorporation": format_date(investor.dob),
            "Occupation Code": investor.get_occupation_display().upper(),
            "Holding Nature": investor.get_holding_nature_display().upper(),
            "Primary Holder PAN": investor.pan,
            "Email": investor.email or investor.user.email,
            "Indian Mobile No.": investor.mobile,
            "Address 1": investor.address_1,
            "Address 2": investor.address_2,
            "Address 3": investor.address_3,
            "City": investor.city,
            "State": investor.state,
            "Pincode": investor.pincode,
            "Country": investor.country or "India",
            "Second Holder First Name": second_first,
            "Second Holder Middle Name": second_middle,
            "Second Holder Last Name": second_last,
            "Second Holder PAN": investor.second_applicant_pan,
            "Third Holder First Name": third_first,
            "Third Holder Middle Name": third_middle,
            "Third Holder Last Name": third_last,
            "Third Holder PAN": investor.third_applicant_pan,
            "Guardian First Name": guardian_first,
            "Guardian Middle Name": guardian_middle,
            "Guardian Last Name": guardian_last,
            "Guardian PAN": investor.guardian_pan,
            "Account No 1": bank_account.account_number if bank_account else "",
            "Bank Name 1": bank_account.bank_name if bank_account else "",
            "Bank Branch 1": bank_account.branch_name if bank_account else "",
            "IFSC Code 1": bank_account.ifsc_code if bank_account else "",
            "Account Type 1": account_type_label(bank_account.account_type) if bank_account else "",
            "Default Bank Flag 1": "Y" if bank_account and bank_account.is_default else "",
            "Nominee 1 Name": nominee.name if nominee else "",
            "Nominee 1 %": decimal_to_string(nominee.percentage) if nominee else "",
            "Nominee 1 Relationship": nominee.relationship if nominee else "",
            "Nominee 1 DOB": format_date(nominee.date_of_birth) if nominee else "",
            "Nominee 1 Guardian": nominee.guardian_name if nominee else "",
        })
    return rows


def build_investor_fatca_rows(queryset):
    rows = []
    for investor in queryset:
        rows.append({
            "PAN_RP": investor.pan,
            "CO_BIR_INC": investor.country_of_birth or "India",
            "PO_BIR_INC": investor.place_of_birth or investor.city or "India",
            "TAX_RES1": investor.country or "India",
            "OCC_CODE": investor.get_occupation_display().upper(),
            "SRCE_WEALT": investor.get_source_of_wealth_display(),
            "INC_SLAB": INCOME_SLAB_LABELS.get(investor.income_slab, investor.get_income_slab_display()),
            "PEP_FLAG": investor.pep_status,
            "SrNo": f"FATCA-{investor.pk:05d}",
        })
    return rows


def build_investor_mandate_rows():
    queryset = Mandate.objects.select_related("investor", "bank_account").filter(
        status=Mandate.APPROVED
    ).order_by("id")
    rows = []
    for mandate in queryset:
        bank_account = mandate.bank_account
        rows.append({
            "MANDATE CODE": mandate.mandate_id,
            "CLIENT CODE": client_code_for(mandate.investor),
            "BANK ACCOUNT NUMBER": bank_account.account_number if bank_account else "",
            "BANK NAME": bank_account.bank_name if bank_account else "",
            "BANK BRANCH": bank_account.branch_name if bank_account else "",
            "STATUS": mandate.status,
            "MANDATE TYPE": MANDATE_TYPE_LABELS.get(mandate.mandate_type, mandate.mandate_type),
            "AMOUNT": decimal_to_string(mandate.amount_limit),
            "START DATE": format_date(mandate.start_date),
            "END DATE": format_date(mandate.end_date),
            "REGN DATE": format_date(mandate.created_at.date() if mandate.created_at else None),
            "APPROVED DATE": format_date(mandate.updated_at.date() if mandate.status == Mandate.APPROVED else None),
            "UMRN NO": mandate.mandate_id,
            "REMARKS": "",
        })
    return rows


def build_investor_sip_rows():
    queryset = SIP.objects.select_related("investor", "scheme", "mandate", "folio").order_by("id")
    rows = []
    for sip in queryset:
        rows.append({
            "SIP Registration Number": sip.bse_reg_no or sip.bse_sip_id or sip.unique_ref_no,
            "PAN": sip.investor.pan,
            "Client Code": client_code_for(sip.investor),
            "Scheme Code": sip.scheme.isin or sip.scheme.scheme_code or "",
            "Mandate Code": sip.mandate.mandate_id if sip.mandate else "",
            "Amount": decimal_to_string(sip.amount),
            "Frequency": sip.frequency,
            "Start Date": format_date(sip.start_date),
            "End Date": format_date(sip.end_date),
            "Installments": sip.installments or "",
            "Status": sip.status,
            "Folio Number": sip.folio.folio_number if sip.folio else "",
        })
    return rows


def build_investor_relationship_rows():
    """Build explicit investor-to-distributor and investor-to-RM mappings."""
    investors = InvestorProfile.objects.select_related(
        "distributor__rm", "rm"
    ).order_by("id")
    rows = []
    for investor in investors:
        distributor = investor.distributor
        rm = investor.rm or (distributor.rm if distributor else None)
        if not distributor and not rm:
            continue

        rows.append({
            "investor_pan": investor.pan,
            "distributor_pan": distributor.pan if distributor else "",
            "rm_code": rm.employee_code if rm else "",
            "distributor_code": distributor.broker_code if distributor else "",
        })
    return rows


def build_folio_distributor_mapping_rows():
    queryset = FolioDistributorMapping.objects.select_related("distributor").order_by(
        "folio_number", "id"
    )
    return [
        {
            "folio_number": mapping.folio_number,
            "distributor_code": mapping.distributor.broker_code,
        }
        for mapping in queryset
    ]


def write_csv(path, headers, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def yes_no(value):
    return "Yes" if value else "No"


def format_date(value):
    return value.isoformat() if value else ""


def decimal_to_string(value):
    if value in (None, ""):
        return ""
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def account_type_label(value):
    return ACCOUNT_TYPE_LABELS.get(value, value or "")


def client_code_for(investor):
    return investor.ucc_code or investor.pan


def split_name(name):
    if not name:
        return "", "", ""
    parts = [part for part in name.split() if part]
    if len(parts) == 1:
        return parts[0], "", ""
    if len(parts) == 2:
        return parts[0], "", parts[1]
    return parts[0], " ".join(parts[1:-1]), parts[-1]


def first_or_none(items):
    return items[0] if items else None
