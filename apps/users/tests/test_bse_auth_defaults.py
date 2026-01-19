import pytest
from apps.users.models import InvestorProfile, User
from apps.integration.utils import map_investor_to_bse_param_string
from datetime import date

@pytest.mark.django_db
def test_map_investor_to_bse_param_string_default_auth_mode():
    """
    Verifies that when an investor is created without specifying auth mode,
    it defaults to 'W' (Wet Signature), which allows orders to proceed without
    immediate online authentication pending state.
    """
    user = User.objects.create(username="defaultauth", first_name="Def", last_name="Ault", email="def@example.com")
    investor = InvestorProfile.objects.create(
        user=user,
        pan="ABCDE1234F",
        dob=date(1990, 1, 1),
        mobile="9876543210",
        address_1="123 Street",
        city="Mumbai",
        state="Maharashtra",
        pincode="400001",
        tax_status=InvestorProfile.INDIVIDUAL,
        occupation=InvestorProfile.SERVICE,
        holding_nature=InvestorProfile.SINGLE,
        nomination_opt='Y',
    )

    # Reload from DB to ensure default is applied
    investor.refresh_from_db()

    param_string = map_investor_to_bse_param_string(investor)
    fields = param_string.split('|')

    # Index 122 corresponds to Field 123 (Nomination Auth Mode)
    auth_mode_value = fields[122]

    assert auth_mode_value == 'W', f"Expected default auth mode 'W', got '{auth_mode_value}'"
