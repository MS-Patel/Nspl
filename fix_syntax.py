with open('apps/reports/services/pdf_generator.py', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'f"Current Value' in line:
        lines[i] = '            "Investment Cost", "Nav", "Units", f"Current Value\\n(As On {fy_end})", "Balance Units"\n'

with open('apps/reports/services/pdf_generator.py', 'w') as f:
    f.writelines(lines)
