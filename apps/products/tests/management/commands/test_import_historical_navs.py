import pytest
from unittest.mock import patch, MagicMock
from django.core.management import call_command
from apps.products.models import Scheme, NAVHistory, AMC
from datetime import date
from decimal import Decimal

@pytest.fixture
def amc():
    return AMC.objects.create(name="Test AMC", code="TEST_AMC")

@pytest.fixture
def scheme(amc):
    return Scheme.objects.create(
        amc=amc,
        name="Test Scheme",
        scheme_code="TEST001",
        isin="INF209K01VH8",
        amfi_code="119436"
    )

@pytest.mark.django_db
def test_import_historical_navs_success(scheme):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "meta": {"scheme_code": 119436},
        "data": [
            {"date": "09-02-2025", "nav": "1037.2300"},
            {"date": "08-02-2025", "nav": "1036.0000"},
        ]
    }

    with patch('requests.get', return_value=mock_response):
        call_command('import_historical_navs')

    assert NAVHistory.objects.count() == 2
    nav1 = NAVHistory.objects.get(nav_date=date(2025, 2, 9))
    assert nav1.net_asset_value == Decimal("1037.2300")

@pytest.mark.django_db
def test_import_historical_navs_api_failure(scheme):
    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch('requests.get', return_value=mock_response):
        call_command('import_historical_navs')

    assert NAVHistory.objects.count() == 0

@pytest.mark.django_db
def test_import_historical_navs_duplicates(scheme):
    # Pre-existing NAV
    NAVHistory.objects.create(
        scheme=scheme,
        nav_date=date(2025, 2, 9),
        net_asset_value=Decimal("1037.2300")
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"date": "09-02-2025", "nav": "1037.2300"}, # Duplicate
            {"date": "08-02-2025", "nav": "1036.0000"}, # New
        ]
    }

    with patch('requests.get', return_value=mock_response):
        call_command('import_historical_navs')

    assert NAVHistory.objects.count() == 2 # 1 existing + 1 new
