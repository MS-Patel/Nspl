import pytest
from decimal import Decimal
from django.utils import timezone
from apps.users.models import User, DistributorProfile, InvestorProfile
from apps.products.models import SchemeCategory, AMC, Scheme
from apps.reconciliation.models import Holding
from apps.payouts.models import CommissionRule, CommissionTier, Payout, PayoutDetail
from apps.payouts.utils import calculate_commission

@pytest.mark.django_db
class TestPayoutCalculation:
    @pytest.fixture
    def setup_data(self):
        # Create Distributor
        self.dist_user = User.objects.create_user(username='dist1', password='password', user_type=User.Types.DISTRIBUTOR)
        self.dist_profile = DistributorProfile.objects.create(user=self.dist_user, arn_number='ARN-12345')

        # Create Investor
        self.inv_user = User.objects.create_user(username='inv1', password='password', user_type=User.Types.INVESTOR)
        self.inv_profile = InvestorProfile.objects.create(user=self.inv_user, distributor=self.dist_profile, pan='ABCDE1234F')

        # Create Product Data
        self.category = SchemeCategory.objects.create(name='Equity')
        self.amc = AMC.objects.create(name='HDFC Mutual Fund')
        self.scheme = Scheme.objects.create(name='HDFC Top 100', category=self.category, amc=self.amc, scheme_code='HDFC001')

        # Create Holding
        self.holding = Holding.objects.create(
            investor=self.inv_profile,
            scheme=self.scheme,
            folio_number='12345/67',
            units=Decimal('100.00'),
            current_value=Decimal('100000.00') # 1 Lakh AUM
        )

        # Create Rule
        self.rule = CommissionRule.objects.create(category=self.category, amc=self.amc)
        self.tier1 = CommissionTier.objects.create(rule=self.rule, min_aum=0, max_aum=5000000, rate=Decimal('0.80')) # < 50L -> 0.8%
        self.tier2 = CommissionTier.objects.create(rule=self.rule, min_aum=5000000, rate=Decimal('1.00')) # >= 50L -> 1%

    def test_calculate_commission_basic(self, setup_data):
        # Run Calculation
        calculate_commission(2023, 10)

        # Verify Payout
        payout = Payout.objects.get(distributor=self.dist_user)
        assert payout.total_aum == Decimal('100000.00')
        # Rate is 0.8% -> 100,000 * 0.008 = 800
        assert payout.total_commission == Decimal('800.00')

        # Verify Detail
        detail = PayoutDetail.objects.get(payout=payout)
        assert detail.scheme_name == 'HDFC Top 100'
        assert detail.applied_rate == Decimal('0.80')
        assert detail.commission_amount == Decimal('800.00')

    def test_calculate_commission_slab_upgrade(self, setup_data):
        # Increase Holding value to 60 Lakhs (crossing 50L threshold)
        self.holding.current_value = Decimal('6000000.00')
        self.holding.save()

        calculate_commission(2023, 10)

        payout = Payout.objects.get(distributor=self.dist_user)
        # Rate should be 1.0% now -> 60,00,000 * 0.01 = 60,000
        assert payout.total_commission == Decimal('60000.00')
        detail = payout.details.first()
        assert detail.applied_rate == Decimal('1.00')

    def test_calculate_commission_no_rule(self, setup_data):
        # Delete rule
        CommissionRule.objects.all().delete()

        calculate_commission(2023, 10)

        payout = Payout.objects.get(distributor=self.dist_user)
        assert payout.total_commission == Decimal('0.00')
        detail = payout.details.first()
        assert detail.applied_rate == Decimal('0.00')

    def test_calculate_commission_global_rule(self, setup_data):
        # Change rule to Global (AMC=None)
        self.rule.amc = None
        self.rule.save()
        # Ensure only one rule exists

        calculate_commission(2023, 10)

        payout = Payout.objects.get(distributor=self.dist_user)
        assert payout.total_commission == Decimal('800.00')
        detail = payout.details.first()
        assert detail.applied_rate == Decimal('0.80')
