from .models import BrokerageTransaction
from apps.reconciliation.models import Holding, Transaction
from django.db.models import Sum

def get_investor_brokerage_analytics(brokerage_import):
    """
    Returns aggregated brokerage earned by investors, along with RM and Distributor info,
    based on the current mapping in the system.
    """
    transactions = BrokerageTransaction.objects.filter(import_file=brokerage_import)

    # 1. Gather all unique folio numbers
    folio_numbers = set(transactions.values_list('folio_number', flat=True))

    # 2. Map folios to investors using Holding table
    holdings = Holding.objects.filter(folio_number__in=folio_numbers).select_related('investor', 'investor__rm', 'investor__rm__user', 'investor__distributor', 'investor__distributor__user')
    folio_to_investor = {}
    for h in holdings:
        folio_to_investor[h.folio_number] = h.investor

    # 3. If any folios missed by holding, check Transaction table
    unmapped_folios = folio_numbers - set(folio_to_investor.keys())
    if unmapped_folios:
        txns = Transaction.objects.filter(folio_number__in=unmapped_folios).exclude(investor__isnull=True).select_related('investor', 'investor__rm', 'investor__rm__user', 'investor__distributor', 'investor__distributor__user')
        for t in txns:
            if t.folio_number not in folio_to_investor:
                folio_to_investor[t.folio_number] = t.investor

    # 4. Aggregate data
    investor_analytics = {}

    for txn in transactions:
        folio = txn.folio_number
        investor = folio_to_investor.get(folio)

        if investor:
            inv_key = f"inv_{investor.id}"
            if inv_key not in investor_analytics:
                investor_name = f"{investor.firstname} {investor.lastname}".strip()
                if not investor_name:
                    investor_name = txn.investor_name or investor.pan

                rm_name_str = ""
                if investor.rm:
                    rm_code = investor.rm.employee_code
                    rm_name = investor.rm.user.name or investor.rm.user.username
                    rm_name_str = f"{investor.rm.employee_code}({rm_name})"

                dist_name_str = ""
                if investor.distributor:
                    dist_name = investor.distributor.user.name or investor.distributor.user.username
                    dist_code = investor.distributor.broker_code
                    dist_name_str = f"{investor.distributor.broker_code}({dist_name})"

                investor_analytics[inv_key] = {
                    'investor_name': investor_name,
                    'pan': investor.pan,
                    'is_direct': not bool(investor.rm or investor.distributor),
                    'rm_name': rm_name_str,
                    'rm_code': rm_code,
                    'distributor_name': dist_name_str,
                    'distributor_code': dist_code,
                    'total_brokerage': 0,
                    'is_mapped_in_system': True
                }
        else:
            # Unmapped investor
            inv_key = f"unmapped_{folio}_{txn.investor_name}"
            if inv_key not in investor_analytics:
                investor_analytics[inv_key] = {
                    'investor_name': txn.investor_name or 'Unknown',
                    'pan': 'Unknown',
                    'is_direct': True, # Treat completely unmapped as direct since we don't know
                    'rm_name': '',
                    'distributor_name': '',
                    'total_brokerage': 0,
                    'is_mapped_in_system': False
                }

        investor_analytics[inv_key]['total_brokerage'] += txn.brokerage_amount

    # Convert to list and calculate summary
    results_list = list(investor_analytics.values())

    summary = {
        'total_brokerage': sum(float(item['total_brokerage']) for item in results_list),
        'direct_brokerage': sum(float(item['total_brokerage']) for item in results_list if item['is_direct']),
        'rm_brokerage': sum(float(item['total_brokerage']) for item in results_list if item['rm_name'] != ''),
        'distributor_brokerage': sum(float(item['total_brokerage']) for item in results_list if item['distributor_name'] != ''),
    }

    return results_list, summary
