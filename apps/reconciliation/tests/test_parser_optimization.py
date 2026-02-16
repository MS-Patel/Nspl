import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.utils import timezone
from apps.reconciliation.parsers import BaseParser
from apps.reconciliation.models import Transaction, RTAFile
from apps.users.models import InvestorProfile, User
from apps.products.models import Scheme, AMC

# Define a concrete parser for testing
class TestParser(BaseParser):
    def parse(self):
        # Simulate processing multiple transactions for the same folio
        pass

@pytest.mark.django_db
class TestParserOptimization:
    def setup_method(self):
        # Create minimal required objects
        self.user = User.objects.create_user(username='testinv', password='password')
        self.investor = InvestorProfile.objects.create(user=self.user, pan='ABCDE1234F')
        self.amc = AMC.objects.create(name='Test AMC', code='101')
        self.scheme = Scheme.objects.create(
            amc=self.amc,
            scheme_code='TESTSCHEME',
            name='Test Scheme',
            isin='INF123456789'
        )
        self.rta_file = RTAFile.objects.create(
            rta_type=RTAFile.RTA_CAMS,
            file_name='test.xls',
            status=RTAFile.STATUS_PENDING
        )
        # Pass a dummy file_path to avoid accessing rta_file.file.path which doesn't exist
        self.parser = TestParser(rta_file_obj=self.rta_file, file_path='/tmp/dummy.xls')

    @patch('apps.reconciliation.parsers.recalculate_holding')
    def test_holding_recalculation_optimization(self, mock_recalculate):
        """
        Verifies that multiple transactions for the same folio only trigger
        recalculate_holding once per folio after processing is complete.
        """
        # Simulate processing 3 transactions for the same folio
        folio_number = '12345'
        date = timezone.now().date()

        # 1. Transaction 1
        self.parser.match_or_create_transaction(
            self.investor, self.scheme, folio_number, 'TXN001', date,
            Decimal('1000.00'), Decimal('10.00'), 'P', 'CAMS'
        )

        # 2. Transaction 2
        self.parser.match_or_create_transaction(
            self.investor, self.scheme, folio_number, 'TXN002', date,
            Decimal('2000.00'), Decimal('20.00'), 'P', 'CAMS'
        )

        # 3. Transaction 3
        self.parser.match_or_create_transaction(
            self.investor, self.scheme, folio_number, 'TXN003', date,
            Decimal('500.00'), Decimal('5.00'), 'P', 'CAMS'
        )

        # Verify initial behavior (before optimization, this would be 3 calls)
        # Verify optimized behavior (we expect 0 calls during processing, 1 after)

        # Currently, match_or_create_transaction calls recalculate_holding immediately.
        # So we expect 3 calls right now.
        # Once optimized, this assertion should fail if we expect 0 calls here.
        # But we want to test the full flow.

        # Simulate the end of parsing
        if hasattr(self.parser, 'process_impacted_holdings'):
            self.parser.process_impacted_holdings()

        # Assertion for Optimized Behavior:
        # We expect exactly 1 call with these arguments
        mock_recalculate.assert_called_with(self.investor, self.scheme, folio_number)

        # Ideally, we want to ensure it was called EXACTLY ONCE, not 3 times.
        # But since the current implementation calls it 3 times, this test will fail if we check for 1.
        # This confirms the "Before" state if we assert 3 calls.
        # This confirms the "After" state if we assert 1 call.

        # Let's assert 1 call to fail initially and pass later.
        assert mock_recalculate.call_count == 1
