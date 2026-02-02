from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from apps.reconciliation.models import RTAFile, Transaction, Holding
from apps.reconciliation.parsers import CAMSParser
from apps.users.models import InvestorProfile, User
from apps.products.models import Scheme, AMC, SchemeCategory
from apps.investments.models import Order, Folio

class ReconciliationLogicTest(TestCase):
    def setUp(self):
        # Setup Master Data
        self.amc = AMC.objects.create(name="HDFC Mutual Fund", code="HDFC")
        self.category = SchemeCategory.objects.create(name="Equity")
        self.scheme = Scheme.objects.create(
            name="HDFC Top 100",
            scheme_code="HDFC100",
            amc=self.amc,
            category=self.category,
            purchase_allowed=True
        )

        # Setup User/Investor
        self.user = User.objects.create_user(username="ABCDE1234F", email="test@example.com", user_type='INVESTOR', name="John Doe")
        self.investor = InvestorProfile.objects.create(
            user=self.user,
            pan="ABCDE1234F",
            email="test@example.com",
            mobile="9999999999"
        )
        self.folio_number = "12345/67"

    def test_bse_allotment_sync_and_rta_matching(self):
        """
        Tests the flow:
        1. Create Provisional Transaction (simulating BSE Sync).
        2. Verify Holding updated.
        3. Parse RTA file matching the transaction.
        4. Verify Transaction confirmed and Holding correct.
        """

        # 1. Simulate BSE Provisional Transaction Creation
        bse_order_id = "BSE10001"
        amount = Decimal("1000.00")
        units = Decimal("10.0000")

        # Manually create what sync_utils would create
        txn = Transaction.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            folio_number=self.folio_number,
            rta_code='BSE',
            txn_type_code='P',
            txn_number=bse_order_id,
            bse_order_id=bse_order_id,
            source=Transaction.SOURCE_BSE,
            is_provisional=True,
            date=timezone.now().date(),
            amount=amount,
            units=units
        )

        # Trigger Recalc (sync_utils does this)
        from apps.reconciliation.utils.reconcile import recalculate_holding
        recalculate_holding(self.investor, self.scheme, self.folio_number)

        # 2. Verify Holding Updated
        holding = Holding.objects.get(investor=self.investor, scheme=self.scheme, folio_number=self.folio_number)
        self.assertEqual(holding.units, units)
        self.assertEqual(holding.free_units, units)
        self.assertEqual(holding.pledged_units, 0)

        # 3. Simulate RTA Import (CAMS)
        # RTA file will have matching Amount, Scheme, Investor, Date
        # But different Txn No (RTA Generated)
        rta_txn_no = "RTA_TXN_999"

        row_data = ["DTL", self.folio_number, "dummy", "HDFC100", "ISIN", "John Doe", "x", "x", "P", rta_txn_no, "x", "x", str(units), str(amount), "x", timezone.now().strftime("%d-%b-%Y"), "x", "x", "ABCDE1234F"]
        while len(row_data) < 20: row_data.append("")

        file_content = "HED|HEADER\n" + "|".join(row_data)
        uploaded_file = SimpleUploadedFile("cams_feed.txt", file_content.encode('utf-8'))
        rta_file = RTAFile.objects.create(rta_type=RTAFile.RTA_CAMS, file_name="cams.txt", file=uploaded_file)

        parser = CAMSParser(rta_file)
        parser.parse()

        # 4. Verify Transaction Confirmed
        txn.refresh_from_db()
        self.assertEqual(txn.txn_number, rta_txn_no) # Updated to RTA ID
        self.assertEqual(txn.source, Transaction.SOURCE_RTA)
        self.assertFalse(txn.is_provisional)
        self.assertEqual(txn.source_file, rta_file)

        # Verify no duplicate created
        self.assertEqual(Transaction.objects.count(), 1)

        # Verify Holding is still correct
        holding.refresh_from_db()
        self.assertEqual(holding.units, units)

    def test_holding_recalculation_logic(self):
        """
        Tests mixed transactions: Purchase, Redemption, Switch.
        """
        recalc_func = lambda: None # Placeholder import
        from apps.reconciliation.utils.reconcile import recalculate_holding

        # Purchase 100 units
        Transaction.objects.create(
            investor=self.investor, scheme=self.scheme, folio_number=self.folio_number,
            txn_type_code='P', txn_number='T1', date=timezone.now().date(),
            amount=1000, units=100
        )

        recalculate_holding(self.investor, self.scheme, self.folio_number)
        h = Holding.objects.get(folio_number=self.folio_number)
        self.assertEqual(h.units, 100)
        self.assertEqual(h.free_units, 100)

        # Redeem 20 units
        Transaction.objects.create(
            investor=self.investor, scheme=self.scheme, folio_number=self.folio_number,
            txn_type_code='R', txn_number='T2', date=timezone.now().date(),
            amount=200, units=20 # Note: Parsers usually store positive units, logic handles sign
        )

        recalculate_holding(self.investor, self.scheme, self.folio_number)
        h.refresh_from_db()
        self.assertEqual(h.units, 80) # 100 - 20
        self.assertEqual(h.free_units, 80)

        # Pledge 10 units
        Transaction.objects.create(
            investor=self.investor, scheme=self.scheme, folio_number=self.folio_number,
            txn_type_code='PL', txn_number='T3', date=timezone.now().date(),
            amount=0, units=10
        )

        recalculate_holding(self.investor, self.scheme, self.folio_number)
        h.refresh_from_db()
        self.assertEqual(h.units, 80) # Total units unchanged
        self.assertEqual(h.pledged_units, 10)
        self.assertEqual(h.free_units, 70) # 80 - 10
