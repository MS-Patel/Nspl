import re

with open('apps/reconciliation/parsers.py', 'r') as f:
    content = f.read()

# CAMS Modifications

content = re.sub(
    r"amount = self\.clean_decimal\(row\.get\('amount'\)\)\n\s*units = self\.clean_decimal\(row\.get\('units'\)\)\n\s*txn_type = str\(row\.get\('trxntype', ''\)\)\.strip\(\)\n\s*txn_stat = str\(row\.get\('trxnstat', ''\)\)\.strip\(\)",
    r"amount = self.clean_decimal(row.get('amount'))\n                        units = self.clean_decimal(row.get('units'))\n                        txn_stat = str(row.get('trxnstat', '')).strip()\n                        \n                        txn_type_code = str(row.get('trxntype', '')).strip()\n                        txn_type = str(row.get('trxn_type_', '')).strip()\n                        tr_flag = str(row.get('trxnmode', '')).strip()",
    content
)

content = re.sub(
    r"remarks = str\(row\.get\('remarks', ''\)\)\.strip\(\)\n\s*tr_flag = str\(row\.get\('trxntype', ''\)\)\.strip\(\).*?# TRXN_TYPE_ mapped to trxn_type_flag in previous code, likely same\n\s*description = txn_nature.*?# Mapping Transaction Nature to description as primary descriptive field\n\s*# Handle NaN",
    r"remarks = str(row.get('remarks', '')).strip()\n                        description = remarks\n\n                        # Handle NaN",
    content,
    flags=re.DOTALL
)

content = re.sub(
    r"# Use trxn_type_ for mapping as requested by user.*?txn_type = str\(row\.get\('trxn_type_', ''\)\)\.strip\(\)",
    r"",
    content,
    flags=re.DOTALL
)

content = re.sub(
    r"parsed_type, parsed_action = get_cams_transaction_type_and_action\(tr_flag\)\n\s*self\.match_or_create_transaction\(\n\s*investor, scheme, folio_number, unique_txn_number, txn_date, amount, units, txn_type, 'CAMS',\n\s*description=description, tr_flag=tr_flag, original_txn_number=original_txn_number, nav=nav,\n\s*raw_data=raw_row_data,\n\s*parsed_txn_type=parsed_type,\n\s*parsed_txn_action=parsed_action,",
    r"_, parsed_action = get_cams_transaction_type_and_action(txn_type_code)\n\n                        self.match_or_create_transaction(\n                            investor, scheme, folio_number, unique_txn_number, txn_date, amount, units, txn_type_code, 'CAMS',\n                            description=description, tr_flag=tr_flag, original_txn_number=original_txn_number, nav=nav,\n                            raw_data=raw_row_data,\n                            parsed_txn_type=txn_type,\n                            parsed_txn_action=parsed_action,",
    content
)

content = re.sub(
    r"amc_code=amc_code, product_code=product_code, txn_nature=txn_type",
    r"amc_code=amc_code, product_code=product_code, txn_nature=txn_nature",
    content
)

with open('apps/reconciliation/parsers.py', 'w') as f:
    f.write(content)
