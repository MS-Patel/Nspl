import os
import openpyxl
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.payouts.utils import calculate_commission
from apps.payouts.models import Payout

class Command(BaseCommand):
    help = 'Calculates distributor commission for a given month and exports to Excel.'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, required=True, help='Year (YYYY)')
        parser.add_argument('--month', type=int, required=True, help='Month (1-12)')
        parser.add_argument('--export', type=str, required=False, help='Path to export Excel file')

    def handle(self, *args, **options):
        year = options['year']
        month = options['month']
        export_path = options['export']

        self.stdout.write(f"Calculating payouts for {month}/{year}...")

        payouts = calculate_commission(year, month)

        self.stdout.write(self.style.SUCCESS(f"Generated {len(payouts)} payout records."))

        if export_path:
            self.export_to_excel(payouts, export_path)

    def export_to_excel(self, payouts, path):
        wb = openpyxl.Workbook()

        # Sheet 1: Summary
        ws_summary = wb.active
        ws_summary.title = "Payout Summary"
        ws_summary.append(["Distributor ID", "Distributor Name", "Period", "Total AUM", "Total Commission", "Status"])

        # Sheet 2: Details
        ws_details = wb.create_sheet("Payout Details")
        ws_details.append(["Distributor Name", "Investor Name", "Folio", "Scheme", "Category", "AMC", "AUM", "Rate (%)", "Commission"])

        for payout in payouts:
            ws_summary.append([
                payout.distributor.id,
                payout.distributor.name or payout.distributor.username,
                payout.period_date.strftime('%Y-%m-%d'),
                payout.total_aum,
                payout.total_commission,
                payout.status
            ])

            for detail in payout.details.all():
                ws_details.append([
                    payout.distributor.name or payout.distributor.username,
                    detail.investor_name,
                    detail.folio_number,
                    detail.scheme_name,
                    detail.category,
                    detail.amc_name,
                    detail.aum,
                    detail.applied_rate,
                    detail.commission_amount
                ])

        wb.save(path)
        self.stdout.write(self.style.SUCCESS(f"Exported to {path}"))
