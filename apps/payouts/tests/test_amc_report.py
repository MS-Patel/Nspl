import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
from apps.payouts.models import BrokerageImport, BrokerageTransaction, Payout, DistributorCategory
from apps.users.models import DistributorProfile
from apps.products.models import AMC, Scheme
import pandas as pd
import io

User = get_user_model()

@pytest.mark.django_db
class TestReports:
    def setup_method(self):
        # Create Admin User
        self.admin = User.objects.create_superuser('admin', 'admin@test.com', 'password')
        self.admin.user_type = User.Types.ADMIN
        self.admin.save()

        # Create Distributor
        self.dist_user = User.objects.create_user('dist1', 'dist1@test.com', 'password')
        self.dist_user.user_type = User.Types.DISTRIBUTOR
        self.dist_profile = DistributorProfile.objects.create(
            user=self.dist_user,
            arn_number='ARN-123',
            broker_code='BBF0001'
        )

        # Create AMC and Schemes
        self.amc1 = AMC.objects.create(name='HDFC Mutual Fund', code='HDFC')
        self.scheme1 = Scheme.objects.create(name='HDFC Top 100 Fund', amc=self.amc1, scheme_code='HDFC1')

        self.amc2 = AMC.objects.create(name='SBI Mutual Fund', code='SBI')
        self.scheme2 = Scheme.objects.create(name='SBI Bluechip Fund', amc=self.amc2, scheme_code='SBI1')

        # Create Import
        self.import_obj = BrokerageImport.objects.create(month=1, year=2024)

        # Create Transactions
        # Txn 1: HDFC, Brokerage 1000
        BrokerageTransaction.objects.create(
            import_file=self.import_obj,
            distributor=self.dist_profile,
            scheme_name='HDFC Top 100 Fund',
            brokerage_amount=Decimal('1000.00'),
            is_mapped=True
        )
        # Txn 2: SBI, Brokerage 500
        BrokerageTransaction.objects.create(
            import_file=self.import_obj,
            distributor=self.dist_profile,
            scheme_name='SBI Bluechip Fund',
            brokerage_amount=Decimal('500.00'),
            is_mapped=True
        )

        # Create Payout (Share 60%)
        Payout.objects.create(
            brokerage_import=self.import_obj,
            distributor=self.dist_profile,
            share_percentage=Decimal('60.00'),
            gross_brokerage=Decimal('1500.00'),
            payable_amount=Decimal('900.00')
        )

    def test_export_payout_report_columns(self, client):
        client.force_login(self.admin)
        url = reverse('payouts:export_payout_report', kwargs={'pk': self.import_obj.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        # Read Excel content
        content = io.BytesIO(response.content)
        df = pd.read_excel(content)

        # Check columns
        assert 'Broker Code' in df.columns
        assert 'Distributor Name' in df.columns

        # Check value
        row = df.iloc[0]
        assert row['Broker Code'] == 'BBF0001'

    def test_export_amc_report_logic(self, client):
        client.force_login(self.admin)
        url = reverse('payouts:export_amc_report', kwargs={'pk': self.import_obj.pk})
        response = client.get(url)

        assert response.status_code == 200

        content = io.BytesIO(response.content)
        df = pd.read_excel(content)

        # Expected:
        # HDFC: Gross 1000, Payable 600 (60%)
        # SBI: Gross 500, Payable 300 (60%)

        hdfc_row = df[df['AMC Name'] == 'HDFC Mutual Fund'].iloc[0]
        assert hdfc_row['Gross Brokerage'] == 1000.0
        assert hdfc_row['Payable Amount'] == 600.0

        sbi_row = df[df['AMC Name'] == 'SBI Mutual Fund'].iloc[0]
        assert sbi_row['Gross Brokerage'] == 500.0
        assert sbi_row['Payable Amount'] == 300.0
