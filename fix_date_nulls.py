import re

with open('apps/reports/services/pdf_generator.py', 'r') as f:
    content = f.read()

# Fix 1: Date parsing (support both string and date objects)
date_parse_logic = """    try:
        if isinstance(fy_start, str):
            start_date = datetime.strptime(fy_start, '%Y-%m-%d').date()
        else:
            start_date = fy_start

        if isinstance(fy_end, str):
            end_date = datetime.strptime(fy_end, '%Y-%m-%d').date()
        else:
            end_date = fy_end
    except:"""

content = re.sub(r'    try:\n        start_date = datetime\.strptime\(fy_start, \'%Y-%m-%d\'\)\.date\(\)\n        end_date = datetime\.strptime\(fy_end, \'%Y-%m-%d\'\)\.date\(\)\n    except:', date_parse_logic, content)

# Fix 2: Null units or amount fallback
null_units_amount_logic = """
            units = pt.units if pt.units else Decimal('0.0000')
            amount = pt.amount if pt.amount else Decimal('0.00')
            if action in ['P', 'SI', 'SIP'] or 'PUR' in action or 'IN' in action:
                opening_units += units
                opening_cost += amount
            elif action in ['R', 'SO', 'SWO'] or 'RED' in action or 'OUT' in action:
                opening_units -= units
                opening_cost -= amount"""

content = re.sub(r'\n\s+if action in \[\'P\', \'SI\', \'SIP\'\] or \'PUR\' in action or \'IN\' in action:\n\s+opening_units \+= pt\.units\n\s+opening_cost \+= pt\.amount\n\s+elif action in \[\'R\', \'SO\', \'SWO\'\] or \'RED\' in action or \'OUT\' in action:\n\s+opening_units -= pt\.units\n\s+opening_cost -= pt\.amount', null_units_amount_logic, content)

null_units_amount_logic2 = """
            units = t.units if t.units else Decimal('0.0000')
            amount = t.amount if t.amount else Decimal('0.00')
            if action in ['P', 'SI', 'SIP'] or 'PUR' in action or 'IN' in action:
                running_units += units
                total_invested_cost += amount
            elif action in ['R', 'SO', 'SWO'] or 'RED' in action or 'OUT' in action:
                running_units -= units
                total_invested_cost -= amount"""

content = re.sub(r'\n\s+if action in \[\'P\', \'SI\', \'SIP\'\] or \'PUR\' in action or \'IN\' in action:\n\s+running_units \+= t\.units\n\s+total_invested_cost \+= t\.amount\n\s+elif action in \[\'R\', \'SO\', \'SWO\'\] or \'RED\' in action or \'OUT\' in action:\n\s+running_units -= t\.units\n\s+total_invested_cost -= t\.amount', null_units_amount_logic2, content)

with open('apps/reports/services/pdf_generator.py', 'w') as f:
    f.write(content)
