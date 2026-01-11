import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.payouts.models import CommissionRule, CommissionTier
from apps.products.factories import SchemeCategoryFactory, AMCFactory

@pytest.mark.django_db
def test_commission_rule_str():
    category = SchemeCategoryFactory(name="Equity")
    rule = CommissionRule.objects.create(category=category)
    assert str(rule) == "Equity - All AMCs"

    amc = AMCFactory(name="HDFC")
    rule_amc = CommissionRule.objects.create(category=category, amc=amc)
    assert str(rule_amc) == "Equity - HDFC"

@pytest.mark.django_db
def test_commission_tier_validation():
    category = SchemeCategoryFactory()
    rule = CommissionRule.objects.create(category=category)

    # Valid Tier
    tier = CommissionTier(rule=rule, min_aum=0, max_aum=100, rate=0.5)
    tier.clean() # Should pass
    tier.save()

    # Invalid Tier (Min >= Max)
    tier_invalid = CommissionTier(rule=rule, min_aum=100, max_aum=50, rate=0.5)
    with pytest.raises(ValidationError):
        tier_invalid.clean()

@pytest.mark.django_db
def test_commission_tier_str():
    category = SchemeCategoryFactory()
    rule = CommissionRule.objects.create(category=category)
    tier = CommissionTier.objects.create(rule=rule, min_aum=0, max_aum=None, rate=Decimal('0.80'))
    assert "Inf" in str(tier)
    assert "0.80%" in str(tier)
