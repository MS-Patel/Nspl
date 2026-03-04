with open('apps/reports/services/pdf_generator.py', 'r') as f:
    content = f.read()

# Let's fix the hardcoded style override in generate_transaction_statement_pdf so the transaction report also uses the same #34495e header color
old_txn_style = """        t_txns.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#34495e')), # Darker grey/blue header"""

if old_txn_style in content:
    print("Already using #34495e in generate_transaction_statement_pdf")
