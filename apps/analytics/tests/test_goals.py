import pytest
from django.urls import reverse
from apps.users.factories import UserFactory, InvestorProfileFactory, DistributorProfileFactory
from apps.analytics.models import Goal, GoalMapping
from apps.reconciliation.models import Holding
from apps.products.models import Scheme, AMC
from decimal import Decimal
from django.utils import timezone
import json

@pytest.fixture
def investor_user():
    user = UserFactory(user_type='INVESTOR')
    InvestorProfileFactory(user=user)
    return user

@pytest.fixture
def distributor_user():
    user = UserFactory(user_type='DISTRIBUTOR')
    dist_profile = DistributorProfileFactory(user=user)
    return user

@pytest.fixture
def holding(investor_user):
    amc = AMC.objects.create(name="Test AMC")
    scheme = Scheme.objects.create(name="Test Scheme", scheme_code="123", amc=amc)
    holding = Holding.objects.create(
        investor=investor_user.investor_profile,
        scheme=scheme,
        folio_number="12345",
        units=100,
        average_cost=10,
        current_nav=20,
        current_value=2000
    )
    return holding

@pytest.mark.django_db
def test_create_goal(client, investor_user):
    client.force_login(investor_user)
    url = reverse('goal_create')
    data = {
        'name': 'Retirement Fund',
        'target_amount': 1000000,
        'target_date': timezone.now().date(),
        'category': 'RETIREMENT',
        'mappings-TOTAL_FORMS': 0,
        'mappings-INITIAL_FORMS': 0,
        'mappings-MIN_NUM_FORMS': 0,
        'mappings-MAX_NUM_FORMS': 1000,
    }
    response = client.post(url, data)
    if response.status_code != 302:
        # Debugging form errors
        print(response.context['form'].errors)
        if 'mappings' in response.context:
            print(response.context['mappings'].errors)

    assert response.status_code == 302
    assert Goal.objects.count() == 1
    goal = Goal.objects.first()
    assert goal.name == 'Retirement Fund'
    assert goal.investor == investor_user.investor_profile

@pytest.mark.django_db
def test_create_goal_with_mapping(client, investor_user, holding):
    client.force_login(investor_user)
    url = reverse('goal_create')
    data = {
        'name': 'Education',
        'target_amount': 500000,
        'target_date': timezone.now().date(),
        'category': 'EDUCATION',
        'mappings-TOTAL_FORMS': 1,
        'mappings-INITIAL_FORMS': 0,
        'mappings-MIN_NUM_FORMS': 0,
        'mappings-MAX_NUM_FORMS': 1000,
        'mappings-0-holding': holding.id,
        'mappings-0-allocation_percentage': 50
    }
    response = client.post(url, data)
    assert response.status_code == 302
    assert Goal.objects.count() == 1
    goal = Goal.objects.first()
    assert goal.mappings.count() == 1
    assert goal.mappings.first().allocation_percentage == 50
    assert goal.current_value == 1000 # 50% of 2000

@pytest.mark.django_db
def test_goal_list_permissions(client, investor_user, distributor_user):
    # Create goal for investor
    Goal.objects.create(
        user=investor_user,
        investor=investor_user.investor_profile,
        name="Specific Unique Goal Name",
        target_amount=1000,
        target_date=timezone.now().date()
    )

    # Investor should see it
    client.force_login(investor_user)
    response = client.get(reverse('goal_list'))
    content = response.content.decode()
    assert "Specific Unique Goal Name" in content

    # Random distributor should NOT see it
    client.force_login(distributor_user)
    response = client.get(reverse('goal_list'))
    content = response.content.decode()
    # Ensure we are checking the Grid JS data, not the title
    assert "Specific Unique Goal Name" not in content

    # Link them
    investor_user.investor_profile.distributor = distributor_user.distributor_profile
    investor_user.investor_profile.save()

    # Now distributor should see it
    response = client.get(reverse('goal_list'))
    content = response.content.decode()
    assert "Specific Unique Goal Name" in content
