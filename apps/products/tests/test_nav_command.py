import pytest
from apps.products.management.commands.fetch_navs import Command
from apps.products.models import Scheme, NAVHistory
from unittest.mock import patch, MagicMock

@pytest.mark.django_db
def test_fetch_navs_command_logic():
    # Setup
    scheme = Scheme.objects.create(
        amc_id=1, # Mock AMC needed? Wait, AMC is FK.
        name="Test Scheme",
        isin="INF209K01VA6", # Example ISIN
        scheme_code="TEST001"
    )

    # We need an AMC first
    from apps.products.models import AMC
    amc = AMC.objects.create(name="Test AMC", code="TAMC")
    scheme.amc = amc
    scheme.save()

    # Mock the fetcher function since we can't hit real URL in tests reliably
    with patch('apps.products.management.commands.fetch_navs.fetch_amfi_navs') as mock_fetch:
        mock_fetch.return_value = True

        cmd = Command()
        cmd.handle()

        mock_fetch.assert_called_once()
