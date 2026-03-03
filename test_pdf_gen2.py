import os
import django
import io

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from apps.reports.services.pdf_generator import generate_transaction_statement_pdf
from apps.users.models import InvestorProfile
from apps.reconciliation.models import Transaction

# We will create mock data since db is empty
from django.contrib.auth import get_user_model
User = get_user_model()
u, _ = User.objects.get_or_create(username="testuser", first_name="Dhaval", last_name="Nanavati")
inv, _ = InvestorProfile.objects.get_or_create(user=u, pan="ABXPN6022F", address_1="A-91 GAKAXY", city="AHMEDABAD", mobile="9925009255")

from apps.products.models import AMC, Scheme
amc, _ = AMC.objects.get_or_create(name="Aditya Birla")
sch1, _ = Scheme.objects.get_or_create(amc=amc, name="Aditya Birla Sun Life Low Duration Fund - Growth", isin="IN123", scheme_code="123")

from datetime import date
from decimal import Decimal
Transaction.objects.get_or_create(investor=inv, scheme=sch1, folio_number="1038402774", date=date(2021, 3, 1), amount=Decimal('16624.20'), nav=Decimal('515.7757'), units=Decimal('32.3860'), tr_flag="P", txn_number="TXN1")
Transaction.objects.get_or_create(investor=inv, scheme=sch1, folio_number="1038402774", date=date(2021, 7, 6), amount=Decimal('16895.65'), nav=Decimal('521.6961'), units=Decimal('32.3860'), tr_flag="SO", txn_number="TXN2")

transactions = Transaction.objects.filter(investor=inv, date__range=[date(2021, 4, 1), date(2022, 3, 31)])

try:
    buffer = generate_transaction_statement_pdf(inv, transactions, fy_start="2021-04-01", fy_end="2022-03-31")
    with open("test_output2.pdf", "wb") as f:
        f.write(buffer.getvalue())
    print("Successfully generated test_output2.pdf")
except Exception as e:
    import traceback
    traceback.print_exc()
