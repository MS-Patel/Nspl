from decimal import Decimal
from datetime import date
from django.test import TestCase
from apps.products.models import Scheme, BSESchemeMapping, NAVHistory
from apps.products.services import get_bse_code, get_latest_nav


class ServicesTests(TestCase):
    def setUp(self):
        self.scheme = Scheme.objects.create(
            name="Sample Scheme",
            normalized_name="sample scheme",
            isin="INF123456789",
            plan_type="DIRECT",
            option="GROWTH"
        )

        # BSE mappings
        self.bse1 = BSESchemeMapping.objects.create(
            scheme=self.scheme,
            bse_code="BSE001",
            transaction_type="LUMPSUM",
            min_amount=Decimal("100.00")
        )
        self.bse2 = BSESchemeMapping.objects.create(
            scheme=self.scheme,
            bse_code="BSE002",
            transaction_type="LUMPSUM",
            min_amount=Decimal("500.00")
        )
        self.bse_sip = BSESchemeMapping.objects.create(
            scheme=self.scheme,
            bse_code="BSESIP1",
            transaction_type="SIP",
            min_amount=Decimal("500.00")
        )

        # NAV records
        self.nav1 = NAVHistory.objects.create(
            scheme=self.scheme,
            nav_date=date(2023, 10, 1),
            net_asset_value=Decimal("10.5000")
        )
        self.nav2 = NAVHistory.objects.create(
            scheme=self.scheme,
            nav_date=date(2023, 10, 5),
            net_asset_value=Decimal("11.0000")
        )
        self.nav3 = NAVHistory.objects.create(
            scheme=self.scheme,
            nav_date=date(2023, 10, 3),
            net_asset_value=Decimal("10.7500")
        )

    def test_get_bse_code_lumpsum_small_amount(self):
        # amount=200, matching LUMPSUM. 100 <= 200, so BSE001 is a candidate. BSE002 is min 500, so it's out.
        bse = get_bse_code(self.scheme, "LUMPSUM", 200.0)
        self.assertEqual(bse, self.bse1)

    def test_get_bse_code_lumpsum_large_amount(self):
        # amount=600. Both BSE001 (min=100) and BSE002 (min=500) are <= 600.
        # Since it orders by "min_amount" ASC and takes the first, it returns BSE001.
        bse = get_bse_code(self.scheme, "LUMPSUM", 600.0)
        self.assertEqual(bse, self.bse1)

    def test_get_bse_code_sip(self):
        bse = get_bse_code(self.scheme, "SIP", 1000.0)
        self.assertEqual(bse, self.bse_sip)

    def test_get_latest_nav(self):
        nav = get_latest_nav(self.scheme)
        self.assertEqual(nav, self.nav2)
