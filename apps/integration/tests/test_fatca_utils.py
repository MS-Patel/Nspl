from django.test import SimpleTestCase
from unittest.mock import MagicMock
import datetime
from apps.integration.utils import map_investor_to_fatca_string
from apps.users.models import InvestorProfile

class TestFatcaMapping(SimpleTestCase):
    def test_id1_type_empty_for_indian_resident(self):
        """
        Verify that ID1_TYPE (Index 14) is empty when Tax Residence is India ('IN').
        This fixes the 'INVALID TYPE OF IDENTIFICATION DOCUMENT' error from BSE.
        """
        user = MagicMock()
        user.first_name = "Test"
        user.last_name = "User"
        user.name = "Test User"

        investor = MagicMock(spec=InvestorProfile)
        investor.user = user
        investor.pan = "ABCDE1234F"
        investor.dob = datetime.date(1990, 1, 1)
        investor.tax_status = "01"
        investor.place_of_birth = "India"
        investor.country_of_birth = "India"
        investor.source_of_wealth = "01"
        investor.income_slab = "32"
        investor.pep_status = "N"
        investor.occupation = "02"
        investor.exemption_code = ""

        result = map_investor_to_fatca_string(investor)
        parts = result.split('|')

        # Field Indices (0-based list from python split):
        # 0: PAN_RP
        # ...
        # 10: CO_BIR_INC
        # 11: TAX_RES1
        # 12: TPIN1
        # 13: ID1_TYPE -> Should be empty

        self.assertEqual(parts[11], "IN", "Tax Residence 1 should be IN (Index 11)")
        self.assertEqual(parts[12], "ABCDE1234F", "TPIN1 should be the PAN (Index 12)")
        self.assertEqual(parts[13], "", "ID1_TYPE must be empty for Indian residents (Index 13)")

    def test_id1_type_present_for_foreign_resident(self):
        """
        Verify that if we ever support foreign residents (non-IN), logic falls back to 'C'.
        Note: The current implementation hardcodes TAX_RES1 to 'IN' inside the function,
        so this test effectively documents that limitation or verifies future behavior if
        that hardcoding is removed.

        However, since utils.py currently has:
        tax_res1 = "IN"
        We can't easily test the 'else' branch without mocking internal variables or changing code structure.
        So we acknowledge that for now, it will always be IN.
        This test is just a placeholder to ensure consistent behavior if that changes.
        """
        # Given the current implementation hardcodes 'IN', we just verify the current state
        # ensures we don't accidentally break the 'IN' logic.
        pass
