import re

with open('apps/reports/services/pdf_generator.py', 'r') as f:
    content = f.read()

# Add add_client_details method to BaseReportGenerator
client_details_method = """
    def add_client_details(self, investor):
        client_name = investor.user.name or investor.user.username if investor and investor.user else "N.A."
        pan = getattr(investor, 'pan', 'N.A.') if investor else "N.A."

        address_parts = []
        if investor:
            if getattr(investor, 'address_1', None): address_parts.append(investor.address_1)
            if getattr(investor, 'address_2', None): address_parts.append(investor.address_2)
            if getattr(investor, 'city', None): address_parts.append(investor.city)
            if getattr(investor, 'state', None): address_parts.append(investor.state)
            if getattr(investor, 'pincode', None): address_parts.append(investor.pincode)
        address = ", ".join(address_parts) if address_parts else "N.A."

        mobile = getattr(investor, 'mobile', 'N.A.') if investor else "N.A."

        client_details_data = [
            [
                Paragraph(f"<b>Client Name :</b><br/>{client_name}<br/>[PAN : {pan}]", self.styles['Normal']),
                Paragraph(f"<b>Address :</b><br/>{address}", self.styles['Normal']),
                Paragraph(f"<b>Mobile :</b><br/>{mobile}", self.styles['Normal']),
                Paragraph(f"<b>Current Sensex :</b><br/>-", self.styles['Normal']) # Dummy sensex
            ]
        ]

        page_width = self.pagesize[0] - self.doc.leftMargin - self.doc.rightMargin
        cd_col_width = page_width / 4.0

        t_cd = Table(client_details_data, colWidths=[cd_col_width]*4)
        t_cd.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f5f7fa')), # Very light blue-grey
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dcdde1')),
        ]))
        self.elements.append(t_cd)
        self.elements.append(Spacer(1, 0.1*inch))
"""

# Find def _create_table to insert client_details_method before it
content = content.replace("    def _create_table(self, data, col_widths=None):", client_details_method + "\n    def _create_table(self, data, col_widths=None):")

# Update _create_table to use dark header styles
old_create_table_style = """        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e0e0e0')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('TOPPADDING', (0,0), (-1,0), 6),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ]))"""

new_create_table_style = """        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#34495e')), # Darker grey/blue header
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ]))"""

content = content.replace(old_create_table_style, new_create_table_style)


# Add generator.add_client_details(investor) in generate_wealth_report_pdf, generate_pl_report_pdf, generate_capital_gain_pdf
content = content.replace(
    "    generator.add_header(title, investor)\n\n    styles = getSampleStyleSheet()",
    "    generator.add_header(title, investor)\n    generator.add_client_details(investor)\n\n    styles = getSampleStyleSheet()"
)

# In generate_transaction_statement_pdf, remove the inline Client Details block
old_txn_client_details = '''    # 1. Client Details Section
    client_name = investor.user.name or investor.user.username if investor and investor.user else "N.A."
    pan = investor.pan if hasattr(investor, 'pan') and investor.pan else "N.A."

    address_parts = []
    if investor:
        if getattr(investor, 'address_1', None): address_parts.append(investor.address_1)
        if getattr(investor, 'address_2', None): address_parts.append(investor.address_2)
        if getattr(investor, 'city', None): address_parts.append(investor.city)
        if getattr(investor, 'state', None): address_parts.append(investor.state)
        if getattr(investor, 'pincode', None): address_parts.append(investor.pincode)
    address = ", ".join(address_parts) if address_parts else "N.A."

    mobile = investor.mobile if hasattr(investor, 'mobile') and investor.mobile else "N.A."

    client_details_data = [
        [
            Paragraph(f"<b>Client Name :</b><br/>{client_name}<br/>[PAN : {pan}]", styles['Normal']),
            Paragraph(f"<b>Address :</b><br/>{address}", styles['Normal']),
            Paragraph(f"<b>Mobile :</b><br/>{mobile}", styles['Normal']),
            Paragraph(f"<b>Current Sensex :</b><br/>-", styles['Normal']) # Dummy sensex
        ]
    ]

    page_width = generator.pagesize[0] - generator.doc.leftMargin - generator.doc.rightMargin
    cd_col_width = page_width / 4.0

    t_cd = Table(client_details_data, colWidths=[cd_col_width]*4)
    t_cd.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f5f7fa')), # Very light blue-grey
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dcdde1')),
    ]))
    generator.elements.append(t_cd)
    generator.elements.append(Spacer(1, 0.1*inch))'''

content = content.replace(old_txn_client_details, "    generator.add_client_details(investor)")

# We need to extract PAN for bank details in transaction statement too
content = content.replace(
    "Paragraph(f\"<b>PAN :</b><br/>{pan}\", styles['Normal'])",
    "Paragraph(f\"<b>PAN :</b><br/>{investor.pan if hasattr(investor, 'pan') and investor.pan else 'N.A.'}\", styles['Normal'])"
)

with open('apps/reports/services/pdf_generator.py', 'w') as f:
    f.write(content)
