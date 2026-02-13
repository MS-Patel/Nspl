import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.users.models import InvestorProfile, Document

User = get_user_model()

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')

# Create a test investor
if not User.objects.filter(username='test_investor').exists():
    inv_user = User.objects.create_user('test_investor', 'inv@example.com', 'password', user_type=User.Types.INVESTOR)
    InvestorProfile.objects.create(
        user=inv_user,
        pan='ABCDE1234F',
        dob='1990-01-01',
        mobile='9999999999',
        address_1='123 Main St',
        city='Metropolis',
        state='NY',
        pincode='10001'
    )
    print("Created test_investor")
else:
    print("test_investor already exists")
