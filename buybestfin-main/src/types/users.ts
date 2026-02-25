export interface Branch {
    id: number;
    name: string;
    code: string;
}

export interface RM {
    id: number;
    name: string;
    username: string;
    email: string;
    employee_code: string;
    branch: number | null;
    branch_name?: string;
    mobile?: string;
    alternate_mobile?: string;
    alternate_email?: string;
    address?: string;
    city?: string;
    state?: string;
    pincode?: string;
    country?: string;
    dob?: string;
    gstin?: string;
    bank_name?: string;
    account_number?: string;
    ifsc_code?: string;
    is_active: boolean;
}

export interface Distributor {
    id: number;
    name: string;
    username: string;
    email: string;
    arn_number?: string;
    broker_code: string;
    rm: number | null;
    rm_name?: string;
    parent?: number | null;
    parent_name?: string;
    is_active: boolean;
    mobile?: string;
    alternate_mobile?: string;
    alternate_email?: string;
    address?: string;
    city?: string;
    state?: string;
    pincode?: string;
    country?: string;
    dob?: string;
    gstin?: string;
    pan?: string;
    bank_name?: string;
    account_number?: string;
    ifsc_code?: string;
}

export interface Investor {
    id: number;
    name: string;
    username: string;
    email: string;
    pan: string;
    status: string;
    distributor_name?: string;
    rm_name?: string;
    is_offline?: boolean;
}
