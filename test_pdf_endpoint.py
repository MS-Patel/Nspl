import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import RequestFactory, TestCase
from apps.users.models import User, InvestorProfile
from apps.investments.views import ExportWealthReportView
from apps.reconciliation.models import Holding
from apps.products.models import Scheme, AMC

class PDFExportTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(email="test@test.com", username="testuser", user_type='ADMIN')
        self.investor = InvestorProfile.objects.create(user=self.user, pan="ABCDE1234F")
        self.amc = AMC.objects.create(name="Test AMC")
        self.scheme = Scheme.objects.create(name="Test Scheme", amc=self.amc)
        self.holding = Holding.objects.create(
            investor=self.investor,
            scheme=self.scheme,
            units=100.0,
            average_cost=10.0,
            current_value=1200.0,
            folio_number="12345"
        )

    def test_wealth_report(self):
        request = self.factory.get(f'/portfolio/{self.investor.id}/export/wealth-report/')
        request.user = self.user

        view = ExportWealthReportView.as_view()
        response = view(request, investor_id=self.investor.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

        # Verify it has some binary content
        self.assertTrue(len(response.content) > 1000)
        print("Wealth Report PDF size:", len(response.content))

    def test_pl_report(self):
        from apps.investments.views import ExportPLReportView
        request = self.factory.get(f'/portfolio/{self.investor.id}/export/pl-report/')
        request.user = self.user

        view = ExportPLReportView.as_view()
        response = view(request, investor_id=self.investor.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        print("P&L Report PDF size:", len(response.content))

    def test_capital_gain(self):
        from apps.investments.views import ExportCapitalGainReportView
        request = self.factory.get(f'/portfolio/{self.investor.id}/export/capital-gain/')
        request.user = self.user

        view = ExportCapitalGainReportView.as_view()
        response = view(request, investor_id=self.investor.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        print("Capital Gain PDF size:", len(response.content))

    def test_transaction_statement(self):
        from apps.investments.views import ExportTransactionStatementView
        request = self.factory.get(f'/portfolio/{self.investor.id}/export/transaction-statement/')
        request.user = self.user

        view = ExportTransactionStatementView.as_view()
        response = view(request, investor_id=self.investor.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        print("Transaction Statement PDF size:", len(response.content))
