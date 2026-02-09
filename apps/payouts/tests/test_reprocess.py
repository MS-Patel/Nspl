import pytest
from decimal import Decimal
from apps.payouts.models import BrokerageImport, BrokerageTransaction, Payout, DistributorCategory
from apps.payouts.utils import reprocess_brokerage_import
from apps.users.models import User, DistributorProfile, InvestorProfile, RMProfile
from apps.reconciliation.models import Holding
from apps.products.models import Scheme, AMC, SchemeCategory

@pytest.mark.django_db
class TestReprocessLogic:
    @pytest.fixture
    def setup_basics(self):
        # Create minimal setup for mapping
        DistributorCategory.objects.create(name='Silver', min_aum=0, max_aum=1000000, share_percentage=60.00)

        # RM & Distributor
        rm_user = User.objects.create(username='rm_reprocess', user_type='RM')
        rm = RMProfile.objects.create(user=rm_user, employee_code='RM888')

        dist_user = User.objects.create(username='dist_reprocess', user_type='DISTRIBUTOR')
        dist = DistributorProfile.objects.create(user=dist_user, arn_number='888888', rm=rm)

        # Investor
        inv_user = User.objects.create(username='inv_reprocess', user_type='INVESTOR')
        investor = InvestorProfile.objects.create(user=inv_user, pan='XYZDE1234F', distributor=dist, rm=rm)

        # Scheme
        amc = AMC.objects.create(name='Test AMC 2', code='TEST2')
        cat = SchemeCategory.objects.create(name='Debt')
        scheme = Scheme.objects.create(name='Test Scheme 2', amc=amc, category=cat)

        return {
            'distributor': dist,
            'investor': investor,
            'scheme': scheme
        }

    def test_reprocess_mapping(self, setup_basics):
        data = setup_basics
        dist = data['distributor']
        investor = data['investor']
        scheme = data['scheme']

        # 1. Create Import
        imp = BrokerageImport.objects.create(month=2, year=2025)

        # 2. Create Unmapped Transaction (Folio '999/999' doesn't exist yet)
        txn = BrokerageTransaction.objects.create(
            import_file=imp,
            source='CAMS',
            folio_number='999/999',
            amount=Decimal('10000'),
            brokerage_amount=Decimal('100'),
            is_mapped=False
        )

        # 3. Run Reprocess - Should fail to map
        mapped_count = reprocess_brokerage_import(imp)
        assert mapped_count == 0
        txn.refresh_from_db()
        assert txn.is_mapped is False

        # 4. Create the missing Holding (which links Folio to Investor -> Distributor)
        Holding.objects.create(
            investor=investor,
            scheme=scheme,
            folio_number='999/999',
            current_value=Decimal('10000'),
            units=100
        )

        # 5. Run Reprocess - Should succeed now
        mapped_count = reprocess_brokerage_import(imp)
        assert mapped_count == 1

        txn.refresh_from_db()
        assert txn.is_mapped is True
        assert txn.distributor == dist
        assert "Mapped via Folio 999/999" in txn.mapping_remark

        # 6. Verify Payout was created
        payout = Payout.objects.filter(brokerage_import=imp, distributor=dist).first()
        assert payout is not None
        assert payout.gross_brokerage == Decimal('100.00')

    def test_reprocess_view(self, client, setup_basics):
        data = setup_basics
        # Create Admin User
        admin_user = User.objects.create(username='admin_reprocess', user_type='ADMIN', is_staff=True, is_superuser=True)
        client.force_login(admin_user)

        # Create Import
        imp = BrokerageImport.objects.create(month=3, year=2025)

        # Call Reprocess View
        response = client.post(f'/payouts/import/{imp.id}/reprocess/', follow=True)

        # Should redirect back to detail view
        assert response.status_code == 200
        assert f'/payouts/import/{imp.id}/' in response.redirect_chain[0][0]
