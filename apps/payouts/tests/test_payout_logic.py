import pytest
from decimal import Decimal
from apps.payouts.models import DistributorCategory, BrokerageImport, BrokerageTransaction, Payout
from apps.payouts.utils import calculate_payouts, get_distributor_category
from apps.users.models import User, DistributorProfile, RMProfile
from apps.reconciliation.models import Holding
from apps.products.models import Scheme, AMC, SchemeCategory

@pytest.mark.django_db
class TestPayoutLogic:
    @pytest.fixture
    def setup_data(self):
        # Create Categories
        DistributorCategory.objects.create(name='Silver', min_aum=0, max_aum=1000000, share_percentage=60.00)
        DistributorCategory.objects.create(name='Gold', min_aum=1000000, max_aum=10000000, share_percentage=75.00)
        DistributorCategory.objects.create(name='Diamond', min_aum=10000000, max_aum=None, share_percentage=90.00)

        # Create Distributor
        rm_user = User.objects.create(username='rm_test', user_type='RM')
        rm = RMProfile.objects.create(user=rm_user, employee_code='RM999')

        dist_user = User.objects.create(username='dist_test', user_type='DISTRIBUTOR')
        dist = DistributorProfile.objects.create(user=dist_user, arn_number='999999', rm=rm)

        # Create Investor & Holding (To simulate AUM)
        inv_user = User.objects.create(username='inv_test', user_type='INVESTOR')

        try:
            investor = inv_user.investor_profile
            investor.distributor = dist
            investor.rm = rm
            investor.save()
        except User.investor_profile.RelatedObjectDoesNotExist:
            from apps.users.models import InvestorProfile
            investor = InvestorProfile.objects.create(user=inv_user, pan='ABCDE1234F', distributor=dist, rm=rm)

        amc = AMC.objects.create(name='Test AMC', code='TEST')
        cat = SchemeCategory.objects.create(name='Equity')
        scheme = Scheme.objects.create(name='Test Scheme', amc=amc, category=cat)

        # Set AUM to 50 Lakhs (Gold Category)
        Holding.objects.create(
            investor=investor,
            scheme=scheme,
            folio_number='123/456',
            current_value=Decimal('5000000'),
            units=100
        )

        return dist

    def test_category_determination(self, setup_data):
        # 50L should be Gold
        cat = get_distributor_category(Decimal('5000000'))
        assert cat.name == 'Gold'
        assert cat.share_percentage == 75.00

        # 5L should be Silver
        cat = get_distributor_category(Decimal('500000'))
        assert cat.name == 'Silver'

        # 2Cr should be Diamond
        cat = get_distributor_category(Decimal('20000000'))
        assert cat.name == 'Diamond'

    def test_payout_calculation(self, setup_data):
        dist = setup_data

        # Create Import
        imp = BrokerageImport.objects.create(month=1, year=2025)

        # Create Transactions linked to this distributor
        BrokerageTransaction.objects.create(
            import_file=imp,
            distributor=dist,
            source='CAMS',
            brokerage_amount=Decimal('1000.00'),
            is_mapped=True
        )
        BrokerageTransaction.objects.create(
            import_file=imp,
            distributor=dist,
            source='KARVY',
            brokerage_amount=Decimal('500.00'),
            is_mapped=True
        )

        # Run Calculation
        calculate_payouts(imp)

        # Verify Payout
        payout = Payout.objects.get(distributor=dist, brokerage_import=imp)

        # AUM: 50,00,000 -> Gold -> 75%
        # Gross: 1500
        # Payable: 1500 * 0.75 = 1125

        assert payout.total_aum == Decimal('5000000')
        assert payout.category == 'Gold'
        assert payout.share_percentage == Decimal('75.00')
        assert payout.gross_brokerage == Decimal('1500.00')
        assert payout.payable_amount == Decimal('1125.00')
