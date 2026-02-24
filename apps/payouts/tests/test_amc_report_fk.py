from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
from apps.payouts.models import BrokerageImport, BrokerageTransaction, Payout
from apps.users.models import DistributorProfile
from apps.products.models import AMC, Scheme
import pandas as pd
import io

User = get_user_model()

class TestReportsWithFK(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser('admin', 'admin@test.com', 'password')

        self.dist_user = User.objects.create_user('dist1', 'dist1@test.com', 'password')
        self.dist_user.user_type = User.Types.DISTRIBUTOR
        self.dist_profile = DistributorProfile.objects.create(
            user=self.dist_user,
            arn_number='ARN-123',
            broker_code='BBF0001'
        )

        self.amc1 = AMC.objects.create(name='HDFC Mutual Fund', code='HDFC')
        self.scheme1 = Scheme.objects.create(name='HDFC Top 100 Fund', amc=self.amc1, scheme_code='HDFC1')

        # Create a scheme where name DOES NOT match AMC logic, to prove FK is used
        self.amc2 = AMC.objects.create(name='Kotak Mutual Fund', code='KOTAK')
        self.scheme2 = Scheme.objects.create(name='Totally Different Name', amc=self.amc2, scheme_code='KOTAK1')

        self.import_obj = BrokerageImport.objects.create(month=1, year=2024)

        # Txn 1: Uses FK, name is garbage. Should map to Kotak.
        BrokerageTransaction.objects.create(
            import_file=self.import_obj,
            distributor=self.dist_profile,
            scheme_name='Garbage Name',
            scheme=self.scheme2, # Points to Kotak
            brokerage_amount=Decimal('1000.00'),
            is_mapped=True
        )

        # Txn 2: No FK, uses Name match. Should map to HDFC.
        BrokerageTransaction.objects.create(
            import_file=self.import_obj,
            distributor=self.dist_profile,
            scheme_name='HDFC Top 100 Fund',
            scheme=None,
            brokerage_amount=Decimal('500.00'),
            is_mapped=True
        )

        # Create payout to link share percentage
        Payout.objects.create(
            brokerage_import=self.import_obj,
            distributor=self.dist_profile,
            share_percentage=Decimal('50.00'),
            gross_brokerage=Decimal('1500.00'),
            payable_amount=Decimal('750.00')
        )

    def test_export_amc_report_uses_fk(self):
        self.client.force_login(self.admin)
        url = reverse('payouts:export_amc_report', kwargs={'pk': self.import_obj.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        content = io.BytesIO(response.content)
        df = pd.read_excel(content)

        # Check Kotak (from FK)
        # Gross 1000, Payable 500 (50%)
        kotak_row = df[df['AMC Name'] == 'Kotak Mutual Fund']
        self.assertFalse(kotak_row.empty)
        self.assertEqual(kotak_row.iloc[0]['Gross Brokerage'], 1000.0)
        self.assertEqual(kotak_row.iloc[0]['Payable Amount'], 500.0)

        # Check HDFC (from Fallback)
        # Gross 500, Payable 250 (50%)
        hdfc_row = df[df['AMC Name'] == 'HDFC Mutual Fund']
        self.assertFalse(hdfc_row.empty)
        self.assertEqual(hdfc_row.iloc[0]['Gross Brokerage'], 500.0)
        self.assertEqual(hdfc_row.iloc[0]['Payable Amount'], 250.0)
