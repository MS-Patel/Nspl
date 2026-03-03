import re

with open('apps/reports/services/pdf_generator.py', 'r') as f:
    content = f.read()

# Fix parsing of datetime and try/except block missing import
date_import_logic = """    from datetime import datetime, date
    try:
        if isinstance(fy_start, str):
            start_date = datetime.strptime(fy_start, '%Y-%m-%d').date()
        else:
            start_date = fy_start

        if isinstance(fy_end, str):
            end_date = datetime.strptime(fy_end, '%Y-%m-%d').date()
        else:
            end_date = fy_end
    except:
        start_date = None"""

content = re.sub(r'    from datetime import datetime\n    try:\n        if isinstance\(fy_start, str\):\n            start_date = datetime\.strptime\(fy_start, \'%Y-%m-%d\'\)\.date\(\)\n        else:\n            start_date = fy_start\n            \n        if isinstance\(fy_end, str\):\n            end_date = datetime\.strptime\(fy_end, \'%Y-%m-%d\'\)\.date\(\)\n        else:\n            end_date = fy_end\n    except:\n        start_date = None', date_import_logic, content)

with open('apps/reports/services/pdf_generator.py', 'w') as f:
    f.write(content)
