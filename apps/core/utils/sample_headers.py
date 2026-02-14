from django.utils.translation import gettext_lazy as _
from apps.users.models import InvestorProfile, DistributorProfile, RMProfile
from apps.products.models import Scheme, NAVHistory
from apps.users.constants import STATE_CHOICES

# --- Investor Sample Headers ---
INVESTOR_HEADERS = [
    'PAN', 'First Name', 'Middle Name', 'Last Name', 'Email', 'Mobile',
    'Tax Status', 'Occupation', 'Holding Nature', 'Source of Wealth', 'Income Slab',
    'PEP Status', 'Place of Birth', 'Country of Birth', 'Exemption Code',
    'Date of Birth (YYYY-MM-DD)', 'Gender',
    'Address 1', 'Address 2', 'Address 3', 'City', 'State', 'Pincode', 'Country',
    'Foreign Address 1', 'Foreign Address 2', 'Foreign Address 3',
    'Foreign City', 'Foreign State', 'Foreign Pincode', 'Foreign Country',
    'Client Type', 'Depository', 'DP ID', 'Client ID',
    'Nominee 1 Name', 'Nominee 1 %', 'Nominee 1 Relationship', 'Nominee 1 DOB', 'Nominee 1 Guardian',
    'Nominee 2 Name', 'Nominee 2 %', 'Nominee 2 Relationship', 'Nominee 2 DOB', 'Nominee 2 Guardian',
    'Nominee 3 Name', 'Nominee 3 %', 'Nominee 3 Relationship', 'Nominee 3 DOB', 'Nominee 3 Guardian',
    'Bank 1 Account No', 'Bank 1 IFSC', 'Bank 1 Type', 'Bank 1 Name', 'Bank 1 Default (Y/N)',
    'Bank 2 Account No', 'Bank 2 IFSC', 'Bank 2 Type', 'Bank 2 Name', 'Bank 2 Default (Y/N)',
    'UCC Code', 'Is Offline (Y/N)'
]

INVESTOR_CHOICES = {
    'Tax Status': [c[1] for c in InvestorProfile.TAX_STATUS_CHOICES],
    'Occupation': [c[1] for c in InvestorProfile.OCCUPATION_CHOICES],
    'Holding Nature': [c[1] for c in InvestorProfile.HOLDING_CHOICES],
    'Source of Wealth': [c[1] for c in InvestorProfile.SOURCE_OF_WEALTH_CHOICES],
    'Income Slab': [c[1] for c in InvestorProfile.INCOME_SLAB_CHOICES],
    'PEP Status': [c[1] for c in InvestorProfile.PEP_CHOICES],
    'Exemption Code': [c[1] for c in InvestorProfile.EXEMPTION_CODE_CHOICES],
    'Gender': ['Male', 'Female', 'Other'],
    'Client Type': [c[1] for c in InvestorProfile.CLIENT_TYPE_CHOICES],
    'Depository': [c[1] for c in InvestorProfile.DEPOSITORY_CHOICES],
    'Nominee 1 Relationship': ['Spouse', 'Father', 'Mother', 'Son', 'Daughter', 'Others'],
    'Nominee 2 Relationship': ['Spouse', 'Father', 'Mother', 'Son', 'Daughter', 'Others'],
    'Nominee 3 Relationship': ['Spouse', 'Father', 'Mother', 'Son', 'Daughter', 'Others'],
    'Bank 1 Type': ['Savings', 'Current', 'NRE', 'NRO'],
    'Bank 2 Type': ['Savings', 'Current', 'NRE', 'NRO'],
    'Bank 1 Default (Y/N)': ['Yes', 'No'],
    'Bank 2 Default (Y/N)': ['Yes', 'No'],
    'Is Offline (Y/N)': ['Yes', 'No'],
}

# --- Distributor Sample Headers ---
DISTRIBUTOR_HEADERS = [
    'ARN', 'Name', 'Email', 'Mobile', 'PAN', 'EUIN',
    'Parent ARN (Optional)', 'RM Employee Code (Optional)',
    'Address', 'City', 'State', 'Pincode', 'Country',
    'Alternate Mobile', 'Alternate Email',
    'Date of Birth', 'GSTIN',
    'Bank Name', 'Account Number', 'IFSC Code', 'Account Type', 'Branch Name',
    'Active Status (Y/N)'
]

DISTRIBUTOR_CHOICES = {
    'Account Type': [c[1] for c in DistributorProfile.ACCOUNT_TYPES],
    'State': [c[1] for c in STATE_CHOICES],
    'Active Status (Y/N)': ['Yes', 'No'],
}

# --- RM Sample Headers ---
RM_HEADERS = [
    'Employee Code', 'Name', 'Email', 'Branch Code',
    'Address', 'City', 'State', 'Pincode', 'Country',
    'Alternate Mobile', 'Alternate Email',
    'Date of Birth', 'GSTIN',
    'Bank Name', 'Account Number', 'IFSC Code', 'Account Type', 'Branch Name',
    'Active Status (Y/N)'
]

RM_CHOICES = {
    'Account Type': [c[1] for c in RMProfile.ACCOUNT_TYPES],
    'State': [c[1] for c in STATE_CHOICES],
    'Active Status (Y/N)': ['Yes', 'No'],
}

# --- Scheme Sample Headers ---
SCHEME_HEADERS = [
    'Scheme Code', 'Scheme Name', 'AMC Code', 'Scheme Type', 'Category', 'ISIN',
    'RTA Scheme Code', 'AMC Scheme Code', 'AMFI Code', 'Unique No',
    'Scheme Plan', 'Purchase Allowed (Y/N)', 'Purchase Transaction Mode',
    'Min Purchase Amount', 'Additional Purchase Amount', 'Max Purchase Amount',
    'Purchase Amount Multiplier', 'Purchase Cutoff Time',
    'Redemption Allowed (Y/N)', 'Redemption Transaction Mode',
    'Min Redemption Qty', 'Redemption Qty Multiplier', 'Max Redemption Qty',
    'Min Redemption Amount', 'Max Redemption Amount', 'Redemption Amount Multiple',
    'Redemption Cutoff Time',
    'SIP Allowed (Y/N)', 'STP Allowed (Y/N)', 'SWP Allowed (Y/N)', 'Switch Allowed (Y/N)',
    'Start Date', 'End Date', 'Reopening Date', 'Face Value', 'Settlement Type',
    'RTA Agent Code', 'AMC Active Flag (Y/N)', 'Dividend Reinvestment Flag (Y/N)',
    'Exit Load Flag (Y/N)', 'Exit Load', 'Lock-in Period Flag (Y/N)', 'Lock-in Period',
    'Channel Partner Code'
]

SCHEME_CHOICES = {
    'Purchase Allowed (Y/N)': ['Yes', 'No'],
    'Redemption Allowed (Y/N)': ['Yes', 'No'],
    'SIP Allowed (Y/N)': ['Yes', 'No'],
    'STP Allowed (Y/N)': ['Yes', 'No'],
    'SWP Allowed (Y/N)': ['Yes', 'No'],
    'Switch Allowed (Y/N)': ['Yes', 'No'],
    'AMC Active Flag (Y/N)': ['Yes', 'No'],
    'Dividend Reinvestment Flag (Y/N)': ['Yes', 'No'],
    'Exit Load Flag (Y/N)': ['Yes', 'No'],
    'Lock-in Period Flag (Y/N)': ['Yes', 'No'],
}

# --- NAV Sample Headers ---
NAV_HEADERS = [
    'Scheme Code', 'NAV Date (YYYY-MM-DD)', 'Net Asset Value',
    'Repurchase Price', 'Sale Price'
]

NAV_CHOICES = {}
