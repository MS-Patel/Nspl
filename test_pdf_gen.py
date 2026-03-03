import os
import django
import io

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from apps.reports.services.pdf_generator import generate_transaction_statement_pdf
from apps.users.models import InvestorProfile
from apps.reconciliation.models import Transaction

investor = InvestorProfile.objects.first()
transactions = Transaction.objects.filter(investor=investor) if investor else []

if investor:
    try:
        buffer = generate_transaction_statement_pdf(investor, transactions, fy_start="2021-04-01", fy_end="2022-03-31")
        with open("test_output.pdf", "wb") as f:
            f.write(buffer.getvalue())
        print("Successfully generated test_output.pdf")
    except Exception as e:
        print(f"Error: {e}")
else:
    print("No investor found to test with.")
