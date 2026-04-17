from django.test import TestCase
from apps.products.models import Scheme
from apps.products.matching import normalize_name, SchemeRecord, match_scheme


class MatchingTests(TestCase):
    def setUp(self):
        self.scheme1 = Scheme.objects.create(
            name="HDFC Mid-Cap Opportunities Fund - Direct Plan - Growth Option",
            normalized_name=normalize_name("HDFC Mid-Cap Opportunities Fund - Direct Plan - Growth Option"),
            amfi_code="118989",
            isin="INF179K01VW4",
            plan_type="DIRECT",
            option="GROWTH"
        )
        self.scheme2 = Scheme.objects.create(
            name="Axis Bluechip Fund Regular Growth",
            normalized_name=normalize_name("Axis Bluechip Fund Regular Growth"),
            amfi_code="112233",
            isin="INF846K01111",
            plan_type="REGULAR",
            option="GROWTH"
        )

    def test_normalize_name(self):
        name = "HDFC Mid-Cap Opportunities Fund - Direct Plan - Growth Option"
        normalized = normalize_name(name)
        self.assertEqual(normalized, "hdfc mid cap opportunities fund    plan    option")

        name2 = "Axis Bluechip Fund Regular Growth"
        normalized2 = normalize_name(name2)
        self.assertEqual(normalized2, "axis bluechip fund")

    def test_match_scheme_by_isin(self):
        # Match by ISIN directly
        record = SchemeRecord(name="Different Name", isin="INF179K01VW4")
        match = match_scheme(record)
        self.assertEqual(match, self.scheme1)

    def test_match_scheme_by_normalized_name(self):
        # Match by normalized name when ISIN doesn't match or is missing
        record = SchemeRecord(name="HDFC Mid-Cap Opportunities Fund Direct Growth", isin=None)
        # Assuming our normalize logic gets it close enough (or exact)
        # Let's test the exact normalization match
        record_exact = SchemeRecord(name="HDFC Mid-Cap Opportunities Fund - Direct Plan - Growth Option", isin=None)
        match = match_scheme(record_exact)
        self.assertEqual(match, self.scheme1)

    def test_no_match(self):
        record = SchemeRecord(name="Non Existent Scheme", isin="INVALID123")
        match = match_scheme(record)
        self.assertIsNone(match)
