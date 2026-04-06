import time
import requests
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from apps.products.models import (
    AMC, Scheme, SchemeCategory, SchemeHolding,
    SchemeSectorAllocation, SchemeRatio
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetches data from mfdata.in and syncs to the local database.'

    def add_arguments(self, parser):
        parser.add_argument('--amcs', action='store_true', help='Sync AMCs')
        parser.add_argument('--schemes', action='store_true', help='Sync Schemes (Families and variants)')
        parser.add_argument('--holdings', action='store_true', help='Sync Holdings and Sectors')
        parser.add_argument('--ratios', action='store_true', help='Sync Ratios')

    def fetch_data(self, endpoint, rate_limit_sleep=2.0):
        url = f"https://mfdata.in{endpoint}"

        try:
            # We respect the rate limits by sleeping
            time.sleep(rate_limit_sleep)
            response = requests.get(url, timeout=10)

            if response.status_code == 429:
                self.stdout.write(self.style.WARNING(f"Rate limited on {url}. Sleeping for 60 seconds..."))
                time.sleep(60)
                response = requests.get(url, timeout=10)

            response.raise_for_status()
            data = response.json()
            if data.get('status') == 'success':
                return data
            else:
                self.stdout.write(self.style.ERROR(f"Error from API on {url}: {data}"))
                return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Request failed for {url}: {e}"))
            return None

    def handle(self, *args, **options):
        if not any([options['amcs'], options['schemes'], options['holdings'], options['ratios']]):
            self.stdout.write(self.style.WARNING("Please provide at least one flag: --amcs, --schemes, --holdings, --ratios"))
            return

        if options['amcs']:
            self.sync_amcs()

        if options['schemes']:
            self.sync_schemes()

        if options['holdings']:
            self.sync_holdings()

        if options['ratios']:
            self.sync_ratios()

    def sync_amcs(self):
        self.stdout.write(self.style.SUCCESS("Starting AMCs sync..."))
        data = self.fetch_data("/api/v1/amcs")
        if not data or not data.get('data'):
            return

        amcs = data.get('data')
        for item in amcs:
            amc_name = item.get('name')
            amc, created = AMC.objects.get_or_create(
                name__iexact=amc_name,
                defaults={'name': amc_name, 'code': amc_name[:20].upper().replace(" ", "")}
            )
            if created:
                self.stdout.write(f"Created new AMC: {amc.name}")
        self.stdout.write(self.style.SUCCESS("AMC sync complete."))

    def sync_schemes(self):
        self.stdout.write(self.style.SUCCESS("Starting Schemes sync..."))

        # We will iterate through schemes in the database and hit the search API
        # using their AMFI code to get the family_id and other details.
        # This is more efficient for our database as we only fetch what we have.
        schemes = Scheme.objects.filter(family_id__isnull=True).exclude(amfi_code__isnull=True).exclude(amfi_code='')

        total_schemes = schemes.count()
        self.stdout.write(f"Found {total_schemes} schemes without family_id but with an AMFI Code.")

        for i, scheme in enumerate(schemes, 1):
            amfi_code = scheme.amfi_code
            self.stdout.write(f"[{i}/{total_schemes}] Fetching details for AMFI: {amfi_code}...")

            # Using the search endpoint to match by AMFI code
            data = self.fetch_data(f"/api/v1/search?q={amfi_code}", rate_limit_sleep=2.0)

            if not data or not data.get('data'):
                # Not found or error
                continue

            results = data.get('data', [])

            # Find the exact match
            match = None
            for r in results:
                if str(r.get('amfi_code')) == str(amfi_code):
                    match = r
                    break

            if match:
                family_id = match.get('family_id')
                if family_id:
                    scheme.family_id = str(family_id)

                    # Also update other fields we might have missed
                    if match.get('expense_ratio') is not None:
                        scheme.expense_ratio = Decimal(str(match.get('expense_ratio')))

                    if match.get('aum') is not None:
                        scheme.aum = Decimal(str(match.get('aum')))

                    # Find category
                    if match.get('category'):
                        category_name = match.get('category')
                        category, _ = SchemeCategory.objects.get_or_create(
                            name=category_name,
                            defaults={'code': category_name[:50].upper().replace(' ', '_')}
                        )
                        scheme.category = category

                    scheme.save()
                    self.stdout.write(self.style.SUCCESS(f"  Matched! Family ID: {family_id}"))

        self.stdout.write(self.style.SUCCESS("Schemes sync complete."))

    def sync_holdings(self):
        self.stdout.write(self.style.SUCCESS("Starting Holdings sync..."))
        # We find schemes that have a family_id
        schemes = Scheme.objects.exclude(family_id__isnull=True).exclude(family_id='')

        # Unique family IDs
        family_ids = set(schemes.values_list('family_id', flat=True))

        self.stdout.write(f"Found {len(family_ids)} families to sync holdings for.")

        for i, fam_id in enumerate(family_ids, 1):
            self.stdout.write(f"[{i}/{len(family_ids)}] Fetching holdings for Family ID: {fam_id}...")
            data = self.fetch_data(f"/api/v1/families/{fam_id}/holdings", rate_limit_sleep=6.0) # Rate limit is 10/min
            if not data or not data.get('data'):
                continue

            holdings_data = data['data']
            equity_holdings = holdings_data.get('equity_holdings', [])
            sectors = holdings_data.get('sectors', [])

            # Find all schemes for this family
            family_schemes = Scheme.objects.filter(family_id=fam_id)

            with transaction.atomic():
                # Delete old holdings for these schemes to avoid duplicates
                SchemeHolding.objects.filter(scheme__in=family_schemes).delete()
                SchemeSectorAllocation.objects.filter(scheme__in=family_schemes).delete()

                # We will populate holdings for each scheme in the family
                for scheme in family_schemes:
                    holdings_to_create = []
                    for h in equity_holdings:
                        holdings_to_create.append(SchemeHolding(
                            scheme=scheme,
                            company_name=h.get('name') or h.get('stock_name') or 'Unknown',
                            percentage=Decimal(str(h.get('weight_pct') or 0)),
                            market_value=Decimal(str(h.get('market_value') or 0)) if h.get('market_value') else None,
                            quantity=Decimal(str(h.get('quantity') or 0)) if h.get('quantity') else None,
                        ))
                    if holdings_to_create:
                        SchemeHolding.objects.bulk_create(holdings_to_create)

                    sector_allocations_to_create = []
                    for s in sectors:
                        sector_allocations_to_create.append(SchemeSectorAllocation(
                            scheme=scheme,
                            sector_name=s.get('sector_name') or 'Unknown',
                            percentage=Decimal(str(s.get('weight_pct') or 0)),
                        ))
                    if sector_allocations_to_create:
                        SchemeSectorAllocation.objects.bulk_create(sector_allocations_to_create)

        self.stdout.write(self.style.SUCCESS("Holdings sync complete."))

    def sync_ratios(self):
        self.stdout.write(self.style.SUCCESS("Starting Ratios sync..."))
        schemes = Scheme.objects.exclude(family_id__isnull=True).exclude(family_id='')
        family_ids = set(schemes.values_list('family_id', flat=True))

        for i, fam_id in enumerate(family_ids, 1):
            self.stdout.write(f"[{i}/{len(family_ids)}] Fetching ratios for Family ID: {fam_id}...")
            data = self.fetch_data(f"/api/v1/families/{fam_id}/ratios", rate_limit_sleep=6.0) # Rate limit is 10/min
            if not data or not data.get('data'):
                continue

            ratio_data = data['data']

            val = ratio_data.get('valuation', {}) or {}
            eff = ratio_data.get('efficiency', {}) or {}
            ret = ratio_data.get('returns', {}) or {}
            risk = ratio_data.get('risk', {}) or {}

            family_schemes = Scheme.objects.filter(family_id=fam_id)

            with transaction.atomic():
                for scheme in family_schemes:
                    SchemeRatio.objects.update_or_create(
                        scheme=scheme,
                        defaults={
                            'as_of_date': datetime.strptime(ratio_data.get('as_of_date'), "%Y-%m-%d").date() if ratio_data.get('as_of_date') else None,
                            'pe_ratio': Decimal(str(val.get('pe_ratio'))) if val.get('pe_ratio') is not None else None,
                            'pb_ratio': Decimal(str(val.get('pb_ratio'))) if val.get('pb_ratio') is not None else None,
                            'ps_ratio': Decimal(str(val.get('ps_ratio'))) if val.get('ps_ratio') is not None else None,
                            'dividend_yield': Decimal(str(val.get('dividend_yield'))) if val.get('dividend_yield') is not None else None,
                            'roe': Decimal(str(eff.get('roe'))) if eff.get('roe') is not None else None,
                            'roa': Decimal(str(eff.get('roa'))) if eff.get('roa') is not None else None,
                            'sharpe_ratio': Decimal(str(ret.get('sharpe_ratio'))) if ret.get('sharpe_ratio') is not None else None,
                            'jensens_alpha': Decimal(str(ret.get('jensens_alpha'))) if ret.get('jensens_alpha') is not None else None,
                            'treynor_ratio': Decimal(str(ret.get('treynor_ratio'))) if ret.get('treynor_ratio') is not None else None,
                            'information_ratio': Decimal(str(ret.get('information_ratio'))) if ret.get('information_ratio') is not None else None,
                            'std_deviation': Decimal(str(risk.get('std_deviation'))) if risk.get('std_deviation') is not None else None,
                            'beta': Decimal(str(risk.get('beta'))) if risk.get('beta') is not None else None,
                            'sortino_ratio': Decimal(str(risk.get('sortino_ratio'))) if risk.get('sortino_ratio') is not None else None,
                            'r_squared': Decimal(str(risk.get('r_squared'))) if risk.get('r_squared') is not None else None,
                        }
                    )
        self.stdout.write(self.style.SUCCESS("Ratios sync complete."))
