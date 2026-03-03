import re

with open('test_pdf_gen2.py', 'r') as f:
    content = f.read()

content = content.replace('u = User.objects.create(', 'u = User.objects.get_or_create(')
content = content.replace('inv = InvestorProfile.objects.create(', 'inv = InvestorProfile.objects.get_or_create(')
content = content.replace('amc = AMC.objects.create(', 'amc = AMC.objects.get_or_create(')
content = content.replace('sch1 = Scheme.objects.create(', 'sch1 = Scheme.objects.get_or_create(')
content = content.replace('Transaction.objects.create(', 'Transaction.objects.get_or_create(')

# Adjust get_or_create tuple unpacks
content = re.sub(r'u = User\.objects\.get_or_create\((.*?)\)', r'u, _ = User.objects.get_or_create(\1)', content)
content = re.sub(r'inv = InvestorProfile\.objects\.get_or_create\((.*?)\)', r'inv, _ = InvestorProfile.objects.get_or_create(\1)', content)
content = re.sub(r'amc = AMC\.objects\.get_or_create\((.*?)\)', r'amc, _ = AMC.objects.get_or_create(\1)', content)
content = re.sub(r'sch1 = Scheme\.objects\.get_or_create\((.*?)\)', r'sch1, _ = Scheme.objects.get_or_create(\1)', content)

with open('test_pdf_gen2.py', 'w') as f:
    f.write(content)
