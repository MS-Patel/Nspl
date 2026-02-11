import pytest
from unittest.mock import MagicMock, patch
from datetime import date
from decimal import Decimal
from apps.products.models import Scheme, NAVHistory, AMC
from apps.products.utils.bse_nav_fetcher import fetch_bse_navs, BSE_NAV_URL

@pytest.fixture
def amc(db):
    return AMC.objects.create(name="Test AMC", code="TEST")

@pytest.mark.django_db
def test_fetch_bse_navs_success(amc):
    # Setup Data
    scheme = Scheme.objects.create(
        amc=amc,
        name="SBI ESG EXCLUSIONARY STRATEGY FUND REGULAR IDCW PAYOUT",
        isin="INF200K01198",
        scheme_code="007-DP",
        unique_no=12345
    )

    # Mock Responses
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.content = b"""
    <html>
        <body>
            <input name="__VIEWSTATE" value="VS123" />
            <input name="__VIEWSTATEGENERATOR" value="GEN123" />
            <input name="__EVENTVALIDATION" value="EV123" />
        </body>
    </html>
    """

    mock_post_response = MagicMock()
    mock_post_response.status_code = 200
    # Sample provided by user
    mock_post_response.text = """
2026-02-10|007-DP|SBI ESG EXCLUSIONARY STRATEGY FUND REGULAR IDCW PAYOUT|007DP|N|INF200K01198|76.6336|CAMS|
    """

    with patch('requests.Session') as MockSession:
        session_instance = MockSession.return_value
        session_instance.get.return_value = mock_get_response
        session_instance.post.return_value = mock_post_response

        # Execute
        result = fetch_bse_navs(date(2026, 2, 10))

        # Verify
        assert result is True

        # Check DB
        nav_entry = NAVHistory.objects.get(scheme=scheme, nav_date=date(2026, 2, 10))
        assert nav_entry.net_asset_value == Decimal('76.6336')

        # Verify Session Calls
        session_instance.get.assert_called_with(BSE_NAV_URL, timeout=30)
        session_instance.post.assert_called_once()
        args, kwargs = session_instance.post.call_args
        assert kwargs['data']['txtToDate'] == '10-Feb-2026'
        assert kwargs['data']['__VIEWSTATE'] == 'VS123'

@pytest.mark.django_db
def test_fetch_bse_navs_html_response_error(amc):
    # Setup Data
    scheme = Scheme.objects.create(
        amc=amc,
        name="Test Scheme",
        isin="INF200K01198",
        scheme_code="007-DP"
    )

    # Mock Responses
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.content = b'<html><input name="__VIEWSTATE" value="VS"/><input name="__EVENTVALIDATION" value="EV"/></html>'

    mock_post_response = MagicMock()
    mock_post_response.status_code = 200
    mock_post_response.text = "<html>Error Page</html>" # Valid HTML returned instead of text file

    with patch('requests.Session') as MockSession:
        session_instance = MockSession.return_value
        session_instance.get.return_value = mock_get_response
        session_instance.post.return_value = mock_post_response

        result = fetch_bse_navs(date(2026, 2, 10))
        assert result is False
