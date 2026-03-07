with open('apps/reconciliation/parsers.py', 'r') as f:
    content = f.read()

content = content.replace("status_desc=txn_stat, remarks=remarks, location=location, txn_nature=txn_nature,", "status_desc=txn_stat, remarks=remarks, location=location,")

with open('apps/reconciliation/parsers.py', 'w') as f:
    f.write(content)
