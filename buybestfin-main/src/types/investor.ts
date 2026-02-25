export interface BankAccount {
    id: number;
    bank_name: string;
    account_number: string;
    ifsc_code: string;
    account_type: string;
    account_type_display: string;
    branch_name: string;
    is_default: boolean;
    bse_index: number | null;
}

export interface Nominee {
    id: number;
    name: string;
    relationship: string;
    relationship_display: string;
    percentage: string; // Decimal string
    date_of_birth: string | null;
    guardian_name: string;
    guardian_pan: string;
    pan: string;
    address_1: string;
    address_2: string;
    address_3: string;
    city: string;
    state: string;
    pincode: string;
    country: string;
    mobile: string;
    email: string;
    id_type: string;
    id_type_display: string;
    id_number: string;
}

export interface Document {
    id: number;
    document_type: string;
    document_type_display: string;
    file_url: string | null;
    uploaded_at: string;
    description: string;
}

export interface Mandate {
    id: number;
    mandate_id: string;
    mandate_type: string;
    mandate_type_display: string;
    amount_limit: string;
    start_date: string;
    end_date: string | null;
    status: string;
    status_display: string;
    bank_account: number | null;
    bank_account_number: string;
    bank_name: string;
    created_at: string;
    updated_at: string;
    is_bse_submitted: boolean;
}

export interface Investor {
    id: number;
    name: string;
    username: string; // PAN
    email: string;
    pan: string;
    mobile: string;
    distributor_name: string | null;
    rm_name: string | null;
    status: string;

    // Details
    dob: string | null;
    gender: string;
    address_1: string;
    address_2: string;
    address_3: string;
    city: string;
    state: string;
    pincode: string;
    country: string;

    // Foreign Address
    foreign_address_1?: string;
    foreign_address_2?: string;
    foreign_address_3?: string;
    foreign_city?: string;
    foreign_state?: string;
    foreign_pincode?: string;
    foreign_country?: string;
    foreign_resi_phone?: string;
    foreign_off_phone?: string;

    // Joint Holders
    second_applicant_name?: string;
    second_applicant_pan?: string;
    second_applicant_dob?: string;
    third_applicant_name?: string;
    third_applicant_pan?: string;
    third_applicant_dob?: string;

    // FATCA
    place_of_birth?: string;
    country_of_birth?: string;
    source_of_wealth?: string;
    source_of_wealth_display?: string;
    income_slab?: string;
    income_slab_display?: string;
    pep_status?: string;
    pep_status_display?: string;
    exemption_code?: string;

    tax_status: string;
    tax_status_display: string;
    occupation: string;
    occupation_display: string;
    holding_nature: string;
    holding_nature_display: string;
    kyc_type: string;
    kyc_type_display: string;

    nominee_auth_status: string;
    nominee_auth_status_display: string;
    ucc_code: string | null;
    bse_remarks: string;
    last_verified_at: string | null;
    kyc_status: boolean;

    bank_accounts: BankAccount[];
    nominees: Nominee[];
    documents: Document[];
    mandates: Mandate[];
}
