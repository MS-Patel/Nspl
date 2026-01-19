import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.users.models import InvestorProfile, DistributorProfile
from apps.users.factories import UserFactory, DistributorProfileFactory, InvestorProfileFactory

User = get_user_model()

def seed_data():
    # 1. Create Distributor
    dist_user = User.objects.filter(username='distributor1').first()
    if not dist_user:
        dist_user = User.objects.create_user(username='distributor1', email='dist@example.com', password='password123', user_type='DISTRIBUTOR')
        DistributorProfile.objects.create(user=dist_user, arn_number='ARN-12345', mobile='9876543210')

    dist_profile = dist_user.distributor_profile

    # 2. Create Investor with Pending Auth
    inv_user = User.objects.filter(username='investor1').first()
    if not inv_user:
        inv_user = User.objects.create_user(username='investor1', email='inv@example.com', password='password123', user_type='INVESTOR', name='John Investor')
        InvestorProfile.objects.create(
            user=inv_user,
            distributor=dist_profile,
            pan='ABCDE1234F',
            mobile='9876543210',
            email='inv@example.com',
            ucc_code='UCC12345',
            nominee_auth_status=InvestorProfile.AUTH_PENDING,
            nomination_opt='Y',
            bse_remarks='NOMINEE AUTHENTICATION PENDING'
        )
    else:
        # Update existing
        inv = inv_user.investor_profile
        inv.nominee_auth_status = InvestorProfile.AUTH_PENDING
        inv.ucc_code = 'UCC12345'
        inv.bse_remarks = 'NOMINEE AUTHENTICATION PENDING'
        inv.save()

    print(f"Seeded Investor ID: {inv_user.investor_profile.pk}")

if __name__ == "__main__":
    seed_data()
