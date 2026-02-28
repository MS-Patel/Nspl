import hashlib
from decimal import Decimal
from datetime import date, datetime
import pandas as pd

def normalize(value):
    """
    Normalizes a value for fingerprint generation.
    Rules:
    - None -> ""
    - Decimal -> remove trailing zeros (format(value.normalize(), "f"))
    - Float -> convert using Decimal(str(value))
    - date/datetime -> ISO format
    - String -> strip() + upper()
    - Everything else -> str(value)
    """
    if pd.isna(value):
        return ""
    if value is None:
        return ""
    if isinstance(value, float):
        value = Decimal(str(value))
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, str):
        return value.strip().upper()
        
    return str(value)

def generate_fingerprint(values: list) -> str:
    """
    Generates a SHA256 fingerprint for a list of values.
    Rules:
    - Normalize all values
    - Join using "|"
    - Encode using UTF-8
    - Hash using SHA256
    - Return hex digest
    """
    normalized_values = [normalize(v) for v in values]
    raw_str = "|".join(normalized_values)
    return hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

def generate_karvy_fingerprint(row_dict: dict) -> str:
    """
    Generates a fingerprint for a KARVY transaction.
    Exact order:
    - "KARVY" (constant)
    - Product Code
    - Folio Number
    - Scheme Code
    - Transaction Number
    - Transaction Date
    - Units
    - Amount
    - Transaction Type
    """
    values = [
        "KARVY",
        row_dict.get('product code'),
        row_dict.get('folio number'),
        row_dict.get('scheme code'),
        row_dict.get('transaction number'),
        row_dict.get('transaction date'),
        row_dict.get('units'),
        row_dict.get('amount'),
        row_dict.get('transaction type')
    ]
    return generate_fingerprint(values)

def generate_cams_fingerprint(row_dict: dict) -> str:
    """
    Generates a fingerprint for a CAMS transaction.
    Exact order:
    - "CAMS" (constant)
    - AMC_CODE
    - FOLIO_NO
    - PRODCODE
    - TRXNNO
    - TRADDATE
    - UNITS
    - AMOUNT
    - TRXN_TYPE_
    - REVERSAL_C (if present)
    """
    values = [
        "CAMS",
        row_dict.get('amc_code'),
        row_dict.get('folio_no'),
        row_dict.get('prodcode'),
        row_dict.get('trxnno'),
        row_dict.get('traddate'),
        row_dict.get('units'),
        row_dict.get('amount'),
        row_dict.get('trxn_type_')
    ]
    
    # Only append reversal_c if it is present and not an empty string or null.
    reversal_c = row_dict.get('reversal_c')
    if pd.notna(reversal_c) and str(reversal_c).strip() != '':
        values.append(reversal_c)
        
    return generate_fingerprint(values)
