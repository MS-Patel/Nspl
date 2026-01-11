from django.test import TestCase
from apps.products.models import Scheme, AMC, SchemeCategory, NAVHistory
from apps.products.utils.nav_fetcher import fetch_amfi_navs
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import date

class NAVFetcherTest(TestCase):
    def setUp(self):
        self.amc = AMC.objects.create(name="Test AMC", code="TEST")
        self.category = SchemeCategory.objects.create(name="Test Cat", code="CAT")
        self.scheme = Scheme.objects.create(
            name="Test Scheme",
            scheme_code="101933",
            isin="INF209K01157",
            amc=self.amc,
            category=self.category
        )

    @patch('apps.products.utils.nav_fetcher.requests.get')
    def test_fetch_amfi_navs(self, mock_get):
        # Mock Response
        mock_content = "101933;INF209K01157;INF209K01165;Test Scheme;150.50;30-Dec-2024"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_content
        mock_get.return_value = mock_response

        fetch_amfi_navs()

        # Check if NAVHistory was created
        nav = NAVHistory.objects.filter(scheme=self.scheme).first()
        self.assertIsNotNone(nav)
        self.assertEqual(nav.net_asset_value, Decimal("150.50"))
        self.assertEqual(nav.nav_date, date(2024, 12, 30))
