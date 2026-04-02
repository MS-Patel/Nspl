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
    Generates a fingerprint for a KARVY transaction using the unified deduplication fields:
    folio_number, scheme_code, txn_type_code, txn_nature, amount, units, date,
    trxnno, siptrxnno, trxn_suffix, scan_ref_no, reversal_code.
    """
    values = [
        "KARVY",
        row_dict.get('folio number'),           # folio_number
        row_dict.get('scheme code'),            # scheme_code
        row_dict.get('transaction type'),       # txn_type_code
        row_dict.get('transaction description'),# txn_nature
        row_dict.get('amount'),                 # amount
        row_dict.get('units'),                  # units
        row_dict.get('transaction date'),       # date
        row_dict.get('transaction number'),     # trxnno
        row_dict.get('purchase transaction no'), # trxnno
        row_dict.get('transaction flag'), # trxnno
        row_dict.get('siptrxnno'),              # siptrxnno (may be None for Karvy but include for consistency)
        row_dict.get('trxn_suffix'),            # trxn_suffix
        row_dict.get('scan_ref_no'),            # scan_ref_no
        row_dict.get('reversal_code')           # reversal_code
    ]
    return generate_fingerprint(values)

def generate_cams_fingerprint(row_dict: dict) -> str:
    """
    Generates a fingerprint for a CAMS transaction using the unified deduplication fields:
    folio_number, scheme_code, txn_type_code, txn_nature, amount, units, date,
    trxnno, siptrxnno, trxn_suffix, scan_ref_no, reversal_code.
    """
    values = [
        "CAMS",
        row_dict.get('folio_no'),               # folio_number
        row_dict.get('prodcode'),               # scheme_code (CAMS prodcode)
        row_dict.get('trxn_type_'),             # txn_type_code (CAMS trxntype)
        row_dict.get('trxn_natur'),             # txn_nature
        row_dict.get('amount'),                 # amount
        row_dict.get('units'),                  # units
        row_dict.get('traddate'),               # date
        row_dict.get('trxnno'),                 # trxnno
        row_dict.get('siptrxnno'),              # siptrxnno
        row_dict.get('trxn_suffi'),             # trxn_suffix
        row_dict.get('scanrefno'),              # scan_ref_no
        row_dict.get('reversal_c')              # reversal_code
    ]
    return generate_fingerprint(values)
