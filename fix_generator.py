with open('apps/reports/services/pdf_generator.py', 'r') as f:
    content = f.read()

# I accidentally added generator.add_client_details twice in generate_transaction_statement_pdf
content = content.replace("    generator.add_header(title, investor)\n    generator.add_client_details(investor)\n\n    styles = getSampleStyleSheet()\n\n    generator.add_client_details(investor)", "    generator.add_header(title, investor)\n    generator.add_client_details(investor)\n\n    styles = getSampleStyleSheet()")

with open('apps/reports/services/pdf_generator.py', 'w') as f:
    f.write(content)
