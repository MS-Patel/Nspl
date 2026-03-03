import re

with open('apps/reports/services/pdf_generator.py', 'r') as f:
    content = f.read()

# Replace generate_transaction_statement_pdf function entirely
new_func = """def generate_transaction_statement_pdf(investor, transactions, fy_start="2024-04-01", fy_end="2025-03-31"):
    buffer = io.BytesIO()
    generator = BaseReportGenerator(buffer, landscape(A4))

    title = f"Transaction Statement For Financial Year - {fy_start} To {fy_end}"
    generator.add_header(title, investor)

    styles = getSampleStyleSheet()

    # 1. Client Details Section
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
    ]))
    generator.elements.append(t_cd)
    generator.elements.append(Spacer(1, 0.1*inch))

    # Import needed models locally to avoid circular imports if any, but better to import at top.
    from apps.reconciliation.models import Transaction, Holding
    from apps.users.models import BankAccount

    # 2. Group transactions by Scheme + Folio
    from collections import defaultdict
    grouped_txns = defaultdict(list)

    # Calculate opening balance: we need all transactions BEFORE fy_start for this investor.
    from django.db.models import Sum
    from django.db.models.functions import Coalesce
    from decimal import Decimal

    # Ensure dates are parsed
    from datetime import datetime
    try:
        start_date = datetime.strptime(fy_start, '%Y-%m-%d').date()
        end_date = datetime.strptime(fy_end, '%Y-%m-%d').date()
    except:
        # Fallback if it's already a date or different format
        start_date = None

    for t in transactions:
        key = (t.scheme, t.folio_number)
        grouped_txns[key].append(t)

    for key, txns_in_period in grouped_txns.items():
        scheme, folio = key

        scheme_name = scheme.name if scheme else "Unknown Scheme"
        generator.elements.append(Paragraph(f"<b>{scheme_name} [{folio}]</b>", styles['Normal']))
        generator.elements.append(Spacer(1, 0.05*inch))

        txn_headers = [
            "Sr. No.", "Transaction Type", "Date", "Transaction Number",
            "Investment Cost", "Nav", "Units", f"Current Value\\n(As On {fy_end})", "Balance Units"
        ]

        # Calculate Opening Balance BEFORE fy_start
        opening_units = Decimal('0.0000')
        opening_cost = Decimal('0.00')

        if start_date:
            past_txns = Transaction.objects.filter(
                investor=investor,
                scheme=scheme,
                folio_number=folio,
                date__lt=start_date
            )
            for pt in past_txns:
                action = pt.txn_type_code.upper() if pt.txn_type_code else pt.tr_flag.upper() if pt.tr_flag else 'P'
                if action in ['P', 'SI', 'SIP'] or 'PUR' in action or 'IN' in action:
                    opening_units += pt.units
                    opening_cost += pt.amount
                elif action in ['R', 'SO', 'SWO'] or 'RED' in action or 'OUT' in action:
                    opening_units -= pt.units
                    opening_cost -= pt.amount

        # Get latest NAV for "Current Value" calculation
        latest_nav = Decimal('0.0000')
        holding = Holding.objects.filter(investor=investor, scheme=scheme, folio_number=folio).first()
        if holding and holding.current_nav:
            latest_nav = holding.current_nav

        txn_data = [txn_headers]

        # Opening Balance Row
        txn_data.append([
            "", "Opening Balance", fy_start, "-", f"{opening_cost:,.2f}", "-", "-", "-", f"{opening_units:,.4f}"
        ])

        running_units = opening_units
        total_invested_cost = opening_cost

        # Transaction Rows
        for idx, t in enumerate(txns_in_period, 1):
            action = t.txn_type_code.upper() if t.txn_type_code else t.tr_flag.upper() if t.tr_flag else 'P'

            # Determine if it adds or subtracts units
            # Usually: Purchase (+), Switch In (+), Redemption (-), Switch Out (-)
            if action in ['P', 'SI', 'SIP'] or 'PUR' in action or 'IN' in action:
                running_units += t.units
                total_invested_cost += t.amount
            elif action in ['R', 'SO', 'SWO'] or 'RED' in action or 'OUT' in action:
                running_units -= t.units
                total_invested_cost -= t.amount

            current_value_txn = t.units * latest_nav if t.units else Decimal('0.00')

            txn_data.append([
                str(idx),
                t.get_txn_type_code_display() if hasattr(t, 'get_txn_type_code_display') else t.txn_type_code,
                t.date.strftime('%Y-%m-%d') if t.date else '',
                t.txn_number if t.txn_number else "-",
                f"{t.amount:,.2f}" if t.amount else "0.00",
                f"{t.nav:,.4f}" if t.nav else "0.0000",
                f"{t.units:,.4f}" if t.units else "0.0000",
                f"{current_value_txn:,.2f}",
                f"{running_units:,.4f}"
            ])

        # Closing Balance Row
        closing_value = running_units * latest_nav
        txn_data.append([
            "", "Closing Balance", fy_end, "-", f"{total_invested_cost:,.2f}", f"{latest_nav:,.4f}", f"{running_units:,.4f}", f"{closing_value:,.2f}", f"{running_units:,.4f}"
        ])

        # Table styling
        col_widths = [0.6*inch, 1.2*inch, 0.8*inch, 1.5*inch, 1.0*inch, 0.8*inch, 0.8*inch, 1.0*inch, 1.0*inch]
        t_txns = generator._create_table(txn_data, col_widths=col_widths)
        t_txns.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e0e0e0')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ]))
        generator.elements.append(t_txns)

        # Bank Details
        bank_details = BankAccount.objects.filter(investor=investor).order_by('-is_default').first()
        bank_name = f"{bank_details.bank_name} - {bank_details.account_number}" if bank_details else "N.A."
        first_holder = investor.user.name or investor.user.username if investor and investor.user else "N.A."
        second_holder = "N.A." # Can be extended if Joint Holders are modeled

        bank_data = [
            [
                Paragraph(f"<b>Bank Details :</b><br/>{bank_name}", styles['Normal']),
                Paragraph(f"<b>First Joint Holder :</b><br/>{first_holder}", styles['Normal']),
                Paragraph(f"<b>PAN :</b><br/>{pan}", styles['Normal']),
                Paragraph(f"<b>Second Joint Holder :</b><br/>{second_holder}", styles['Normal']),
                Paragraph(f"<b>PAN :</b><br/>N.A.", styles['Normal'])
            ]
        ]
        bd_col_widths = [2.5*inch, 2.0*inch, 1.2*inch, 2.0*inch, 1.0*inch]
        t_bank = Table(bank_data, colWidths=bd_col_widths)
        t_bank.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ]))
        generator.elements.append(t_bank)
        generator.elements.append(Spacer(1, 0.2*inch))

    if not grouped_txns:
        txn_headers = ["Date", "Transaction Type", "Folio Number", "Amount", "NAV", "Units"]
        t_txns = generator._create_table([txn_headers, ["No transactions found for this period.", "", "", "", "", ""]])
        generator.elements.append(t_txns)

    generator.build()
    buffer.seek(0)
    return buffer"""

content = re.sub(r'def generate_transaction_statement_pdf.*?return buffer\s*', new_func + '\n', content, flags=re.DOTALL)

with open('apps/reports/services/pdf_generator.py', 'w') as f:
    f.write(content)
