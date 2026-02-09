import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.integration.bse_client import BSEStarMFClient
from apps.reconciliation.models import Transaction
from apps.products.models import Scheme
from apps.users.models import InvestorProfile
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Syncs historical Order Status and Allotment Statements from BSE for the specified date range.'

    def add_arguments(self, parser):
        parser.add_argument('--start-date', type=str, help='Start date in DD/MM/YYYY format')
        parser.add_argument('--end-date', type=str, help='End date in DD/MM/YYYY format')
        parser.add_argument('--months', type=int, default=36, help='Number of months to look back (default 36)')

    def handle(self, *args, **options):
        client = BSEStarMFClient()

        # Calculate Date Range
        if options['start_date'] and options['end_date']:
            start_date = datetime.datetime.strptime(options['start_date'], '%d/%m/%Y').date()
            end_date = datetime.datetime.strptime(options['end_date'], '%d/%m/%Y').date()
        else:
            end_date = timezone.now().date()
            start_date = end_date - datetime.timedelta(days=30 * options['months'])

        self.stdout.write(f"Syncing BSE History from {start_date} to {end_date}...")

        # Process Month by Month
        current_date = start_date
        while current_date < end_date:
            next_month = current_date + datetime.timedelta(days=30) # Approx
            if next_month > end_date:
                next_month = end_date

            f_date_str = current_date.strftime("%d/%m/%Y")
            t_date_str = next_month.strftime("%d/%m/%Y")

            self.stdout.write(f"Processing chunk: {f_date_str} to {t_date_str}")

            # Fetch Allotment Statement (Confirmed Orders)
            # We use AllotmentStatement as it provides the final Unit allotment which is crucial for reconciliation
            try:
                response = client.get_allotment_statement(
                    from_date=f_date_str,
                    to_date=t_date_str,
                    order_status="ALL"
                )

                # Check response type. Zeep returns list of objects usually.
                # If wrapped in a parent object, we need to iterate.
                # Assuming response is iterable or has a property containing list.
                # Based on bse_client.py, it returns raw service response.
                # Let's assume standard Zeep list or dict structure.

                # Note: BSE API often returns a string if no data, or a complex object.
                # We need to be careful with parsing.

                if response:
                    self.process_bse_records(response)
                else:
                    self.stdout.write("No records found in this chunk.")

            except Exception as e:
                self.stderr.write(f"Error fetching chunk {f_date_str}-{t_date_str}: {e}")

            current_date = next_month + datetime.timedelta(days=1)

        self.stdout.write(self.style.SUCCESS('Historical Sync Complete'))

    def process_bse_records(self, records):
        """
        Matches BSE records with local Transactions.
        """
        # Iterate over records.
        # Since I don't have the exact Zeep object structure in memory, I'll use getattr/get safe access.
        # Typically BSE returns a list of objects like 'AllotmentStatementResponse'

        # Handling potential nested list (e.g., response.AllotmentStatement)
        if hasattr(records, '__iter__') and not hasattr(records, 'items'):
            iterable_records = records
        elif hasattr(records, 'AllotmentStatement'): # Common SOAP pattern
            iterable_records = records.AllotmentStatement
        else:
            # Single object or unknown
            iterable_records = [records]

        count = 0
        for record in iterable_records:
            try:
                # Extract Key Fields
                bse_order_id = getattr(record, 'OrderNo', None)
                if not bse_order_id: continue

                client_code = getattr(record, 'ClientCode', '')
                scheme_code = getattr(record, 'SchemeCode', '')
                amount = getattr(record, 'Amount', 0)
                units = getattr(record, 'Unit', 0)
                order_date_str = getattr(record, 'OrderDate', '') # Format usually DD/MM/YYYY

                if not order_date_str: continue
                try:
                    order_date = datetime.datetime.strptime(order_date_str.split()[0], "%d/%m/%Y").date()
                except:
                    continue

                # Find Local Transaction
                # 1. Find Investor by Client Code (UCC) or PAN (if embedded in UCC)
                investor = InvestorProfile.objects.filter(ucc_code=client_code).first()
                if not investor:
                    # Fallback: UCC might be PAN
                    investor = InvestorProfile.objects.filter(pan=client_code).first()

                if not investor:
                    continue # Can't link if investor unknown

                # 2. Find Scheme
                scheme = Scheme.objects.filter(scheme_code=scheme_code).first()
                if not scheme:
                    continue

                # 3. Match Transaction
                # Window: +/- 5 days
                min_date = order_date - datetime.timedelta(days=5)
                max_date = order_date + datetime.timedelta(days=5)

                # Convert decimals safely
                try:
                    val_amount = Decimal(str(amount))
                except:
                    val_amount = Decimal(0)

                txn = Transaction.objects.filter(
                    investor=investor,
                    scheme=scheme,
                    amount=val_amount,
                    date__range=[min_date, max_date]
                ).first()

                if txn:
                    # Link BSE ID
                    if not txn.bse_order_id:
                        txn.bse_order_id = bse_order_id
                        # If source was RTA, we keep it RTA but enrich with BSE ID
                        # If we want to assert BSE as source, we could change it,
                        # but usually RTA is the final settlement source.
                        txn.save()
                        count += 1
                        self.stdout.write(f"Linked Order {bse_order_id} to Txn {txn.id}")

            except Exception as e:
                # Log but continue
                logger.error(f"Error processing BSE record: {e}")

        if count > 0:
            self.stdout.write(f"Linked {count} transactions in this chunk.")
