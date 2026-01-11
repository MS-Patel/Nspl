import pytest
from django.urls import reverse
from apps.users.factories import UserFactory
from apps.products.factories import SchemeCategoryFactory, AMCFactory
from apps.payouts.models import CommissionRule

@pytest.mark.django_db
class TestCommissionRuleViews:
    def test_list_view_access(self, client):
        admin = UserFactory(user_type='ADMIN')
        client.force_login(admin)
        url = reverse('payout_rule_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_list_view_forbidden(self, client):
        user = UserFactory(user_type='DISTRIBUTOR')
        client.force_login(user)
        url = reverse('payout_rule_list')
        response = client.get(url)
        assert response.status_code == 403

    def test_create_rule(self, client):
        admin = UserFactory(user_type='ADMIN')
        category = SchemeCategoryFactory()
        client.force_login(admin)

        url = reverse('payout_rule_create')
        data = {
            'category': category.id,
            'tiers-TOTAL_FORMS': 1,
            'tiers-INITIAL_FORMS': 0,
            'tiers-MIN_NUM_FORMS': 0,
            'tiers-MAX_NUM_FORMS': 1000,
            'tiers-0-min_aum': 0,
            'tiers-0-max_aum': '',
            'tiers-0-rate': 0.8
        }
        response = client.post(url, data)
        assert response.status_code == 302 # Redirects on success
        assert CommissionRule.objects.count() == 1
        assert CommissionRule.objects.first().tiers.count() == 1

    def test_update_rule(self, client):
        admin = UserFactory(user_type='ADMIN')
        category = SchemeCategoryFactory()
        rule = CommissionRule.objects.create(category=category)
        client.force_login(admin)

        url = reverse('payout_rule_update', args=[rule.id])
        data = {
            'category': category.id,
            'tiers-TOTAL_FORMS': 1,
            'tiers-INITIAL_FORMS': 0,
            'tiers-MIN_NUM_FORMS': 0,
            'tiers-MAX_NUM_FORMS': 1000,
            'tiers-0-min_aum': 0,
            'tiers-0-max_aum': '',
            'tiers-0-rate': 1.0 # Update rate
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert rule.tiers.first().rate == 1.0
