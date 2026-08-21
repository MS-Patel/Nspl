import pytest
from apps.users.models import InvestorProfile, User
from apps.users.models import Nominee
from apps.integration.utils import get_rel_code, map_investor_to_bse_param_string
from datetime import date

@pytest.mark.django_db
def test_map_investor_to_bse_param_string_183_fields():
    # Setup
    user = User.objects.create(username="testinv", first_name="John", last_name="Doe", email="john@example.com")
    investor = InvestorProfile.objects.create(
        user=user,
        firstname="John",
        lastname="Doe",
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
        nomination_opt='N',
        nomination_auth_mode='O'
    )

    # Execute
    param_string = map_investor_to_bse_param_string(investor)

    # Verify
    fields = param_string.split('|')
    print(f"Total Fields: {len(fields)}")

    # Assert
    assert len(fields) == 183, f"Expected 183 fields, got {len(fields)}"
    assert fields[0] == "ABCDE1234F" # Client Code (defaults to PAN)
    assert fields[1] == "John" # First Name

    # Check Fillers
    assert fields[182] == "" # Last filler (Index 182 = Field 183)

@pytest.mark.django_db
def test_map_investor_with_nominees():
    user = User.objects.create(username="nomtest", first_name="Jane", last_name="Doe")
    investor = InvestorProfile.objects.create(
        user=user,
        firstname="Jane",
        lastname="Doe",
        pan="FGHIJ5678K",
        dob=date(1985, 5, 5),
        mobile="9999999999",
        address_1="456 Ave",
        city="Delhi",
        state="Delhi",
        pincode="110001",
        nomination_opt='Y',
        nomination_auth_mode='O'
    )

    # Add Nominee
    from apps.users.models import Nominee
    Nominee.objects.create(
        investor=investor,
        name="Nominee One",
        relationship="Spouse",
        percentage=100,
        date_of_birth=date(1990, 1, 1),
        pan="XYZ123",
        address_1="Nom Addr 1",
        city="Nom City",
        pincode="999999"
    )

    param_string = map_investor_to_bse_param_string(investor)
    fields = param_string.split('|')

    assert len(fields) == 183


def test_nominee_relationship_choices_cover_the_bse_v183_list():
    expected_relationships = [
        'Aunt', 'Brother-in-law', 'Brother', 'Daughter', 'Daughter-in-law',
        'Father', 'Father-in-law', 'Grand Daughter', 'Grand Father',
        'Grand Mother', 'Grand Son', 'Mother-in-law', 'Mother', 'Nephew',
        'Niece', 'Sister', 'Sister-in-law', 'Son', 'Son-in-law', 'Spouse',
        'Uncle', 'Others', 'Court Appointed Legal Guardian',
    ]

    assert [value for value, _label in Nominee.RELATIONSHIP_CHOICES] == expected_relationships
    assert [get_rel_code(relationship) for relationship in expected_relationships] == [
        f'{code:02d}' for code in range(1, 24)
    ]
