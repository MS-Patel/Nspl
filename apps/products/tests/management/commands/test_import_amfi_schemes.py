import os
import tempfile
from django.test import TestCase
from django.core.management import call_command
from apps.products.models import Scheme, AMC, SchemeCategory

class ImportAmfiSchemesTest(TestCase):

    def setUp(self):
        # Create dependencies
        self.amc = AMC.objects.create(name="Test AMC", code="TESTAMC")
        self.category = SchemeCategory.objects.create(name="Test Category", code="TESTCAT")

        # Create two schemes with same ISIN but different scheme_code
        self.isin = "INF123456789"

        self.scheme1 = Scheme.objects.create(
            amc=self.amc,
            category=self.category,
            name="Test Scheme 1 - Growth",
            isin=self.isin,
            scheme_code="SCHEME1",
            unique_no=1001,
            amfi_code=None  # Initially None
        )

        self.scheme2 = Scheme.objects.create(
            amc=self.amc,
            category=self.category,
            name="Test Scheme 1 - Dividend",
            isin=self.isin,
            scheme_code="SCHEME2",
            unique_no=1002,
            amfi_code=None  # Initially None
        )

    def test_import_amfi_schemes_duplicate_isin(self):
        """
        Test that import_amfi_schemes command updates all schemes sharing the same ISIN.
        """
        amfi_code = "111111"

        # Create a temporary CSV file
        csv_content = f"Code,ISIN Div Payout/ ISIN Growth,ISIN Div Reinvestment,Scheme Name\n{amfi_code},{self.isin},,Test Scheme 1"

        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv') as temp_csv:
            temp_csv.write(csv_content)
            temp_csv_path = temp_csv.name

        try:
            # Run the command
            call_command('import_amfi_schemes', temp_csv_path)

            # Refresh from DB
            self.scheme1.refresh_from_db()
            self.scheme2.refresh_from_db()

            # Assertions
            self.assertEqual(self.scheme1.amfi_code, amfi_code, "Scheme 1 should have been updated with AMFI code")
            self.assertEqual(self.scheme2.amfi_code, amfi_code, "Scheme 2 should have been updated with AMFI code")

        finally:
            if os.path.exists(temp_csv_path):
                os.remove(temp_csv_path)
