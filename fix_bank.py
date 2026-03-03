import re

with open('apps/reports/services/pdf_generator.py', 'r') as f:
    content = f.read()

# Replace bank_details fetch logic to consider folio-specific details via Transaction
bank_logic = """        # Bank Details
        bank_details = None
        # Try to get bank details from any transaction in this folio
        for t in txns_in_period:
            if t.bank_account_no:
                bank_name = f"{t.bank_name or 'Bank'} - {t.bank_account_no}"
                bank_details = True
                break

        if not bank_details:
            bank_acc = BankAccount.objects.filter(investor=investor).order_by('-is_default').first()
            bank_name = f"{bank_acc.bank_name} - {bank_acc.account_number}" if bank_acc else "N.A."
        """

content = re.sub(r'        # Bank Details\s+bank_details = BankAccount\.objects\.filter\(investor=investor\)\.order_by\(\'-is_default\'\)\.first\(\)\s+bank_name = f"\{bank_details\.bank_name\} - \{bank_details\.account_number\}" if bank_details else "N\.A\."', bank_logic, content)

with open('apps/reports/services/pdf_generator.py', 'w') as f:
    f.write(content)
