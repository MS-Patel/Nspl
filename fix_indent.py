with open('apps/reconciliation/parsers.py', 'r') as f:
    lines = f.readlines()

with open('apps/reconciliation/parsers.py', 'w') as f:
    for line in lines:
        if "_, parsed_action = get_cams_transaction_type_and_action(txn_type_code)" in line:
            f.write("                        _, parsed_action = get_cams_transaction_type_and_action(txn_type_code)\n")
        else:
            f.write(line)
