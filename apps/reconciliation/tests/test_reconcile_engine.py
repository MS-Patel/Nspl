import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from apps.reconciliation.models import Transaction, OrderReconciliation
from apps.reconciliation.services.reconcile_engine import ReconcileEngine
from apps.users.models import InvestorProfile, User
from apps.products.models import Scheme, AMC

@pytest.mark.django_db
class TestReconcileEngine:
    def setup_method(self):
        self.user = User.objects.create_user(username='reconuser', password='password')
        self.investor = InvestorProfile.objects.create(user=self.user, pan='RECON1234F')
        self.amc = AMC.objects.create(name='Recon AMC', code='REC')
        self.scheme = Scheme.objects.create(amc=self.amc, scheme_code='RECSCHEME')
        self.engine = ReconcileEngine()

    def test_perfect_match(self):
        # Create an UNKNOWN transaction from RTA
        order_date = timezone.now().date()
        txn = Transaction.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            folio_number='FOLIO1',
            date=order_date,
            amount=Decimal('1000.00'),
            units=Decimal('10.00'),
            origin=Transaction.ORIGIN_UNKNOWN,
            fingerprint='FINGER1',
            is_provisional=False
        )

        # Attempt to match an identical order
        recon = self.engine.match_bse_order(
            bse_order_id='BSE1001',
            investor=self.investor,
            scheme=self.scheme,
            amount=Decimal('1000.00'),
            order_date=order_date,
            folio_number='FOLIO1'
        )

        txn.refresh_from_db()
        assert recon.status == OrderReconciliation.STATUS_MATCHED
        assert recon.confidence_score >= 0.9 # Folio(0.4) + Scheme(0.2) + Amount(0.2) + Date(0.2) = 1.0
        assert txn.origin == Transaction.ORIGIN_BSE
        assert txn.bse_order_id == 'BSE1001'

    def test_partial_match(self):
        # Folio mismatch, but everything else matches
        order_date = timezone.now().date()
        txn = Transaction.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            folio_number='FOLIO_WRONG',
            date=order_date,
            amount=Decimal('1000.00'),
            units=Decimal('10.00'),
            origin=Transaction.ORIGIN_UNKNOWN,
            fingerprint='FINGER2'
        )

        recon = self.engine.match_bse_order(
            bse_order_id='BSE1002',
            investor=self.investor,
            scheme=self.scheme,
            amount=Decimal('1000.00'),
            order_date=order_date,
            folio_number='FOLIO_EXPECTED'
        )

        txn.refresh_from_db()
        # Scheme(0.2) + Amount(0.2) + Date(0.2) = 0.6
        # Wait, the threshold for PARTIAL is 0.7. So this should be a MISMATCH.
        assert recon.status == OrderReconciliation.STATUS_MISMATCH
        assert txn.origin == Transaction.ORIGIN_UNKNOWN

    def test_sip_match(self):
        order_date = timezone.now().date()
        txn = Transaction.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            folio_number='FOLIO1',
            date=order_date,
            amount=Decimal('500.00'),
            units=Decimal('5.00'),
            origin=Transaction.ORIGIN_UNKNOWN,
            fingerprint='FINGER3',
            siptrxnno='SIP12345'
        )

        recon = self.engine.match_bse_order(
            bse_order_id='BSE1003',
            investor=self.investor,
            scheme=self.scheme,
            amount=Decimal('500.00'),
            order_date=order_date,
            folio_number='FOLIO1',
            sip_reg_no='SIP12345'
        )

        assert recon.status == OrderReconciliation.STATUS_MATCHED
        # Folio(0.4) + Scheme(0.2) + Amt(0.2) + Date(0.2) + SIP(0.5) = 1.5
        assert recon.confidence_score == 1.5

    def test_reversal_penalty(self):
        order_date = timezone.now().date()
        txn = Transaction.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            folio_number='FOLIO1',
            date=order_date,
            amount=Decimal('1000.00'),
            units=Decimal('10.00'),
            origin=Transaction.ORIGIN_UNKNOWN,
            fingerprint='FINGER4',
            reversal_code='REV'
        )

        recon = self.engine.match_bse_order(
            bse_order_id='BSE1004',
            investor=self.investor,
            scheme=self.scheme,
            amount=Decimal('1000.00'),
            order_date=order_date,
            folio_number='FOLIO1'
        )

        # Base 1.0 - Reversal Penalty 1.0 = 0.0
        assert recon.status == OrderReconciliation.STATUS_MISMATCH
