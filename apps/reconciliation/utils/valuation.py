from decimal import Decimal
from django.db.models import Sum, F, OuterRef, Subquery
from django.utils import timezone
from apps.products.models import NAVHistory
from apps.reconciliation.models import Holding

def calculate_portfolio_valuation(investor_profile):
    """
    Updates current value of holdings for an investor and returns summary.
    """
    # Subquery to fetch the latest NAV for the scheme
    latest_nav_qs = NAVHistory.objects.filter(
        scheme=OuterRef('scheme')
    ).order_by('-nav_date')

    # Fetch holdings with scheme pre-fetched and annotated with latest NAV details
    holdings = Holding.objects.filter(investor=investor_profile).select_related('scheme').annotate(
        latest_nav_val=Subquery(latest_nav_qs.values('net_asset_value')[:1]),
        latest_nav_date=Subquery(latest_nav_qs.values('nav_date')[:1])
    )

    total_current_value = Decimal(0)
    total_invested_value = Decimal(0)

    holdings_data = []
    holdings_to_update = []

    # Timestamp for bulk update
    now = timezone.now()

    for holding in holdings:
        scheme = holding.scheme
        nav_val = holding.latest_nav_val
        nav_date = holding.latest_nav_date

        if nav_val is not None:
            holding.current_nav = nav_val
            holding.current_value = holding.units * nav_val
            holding.last_updated = now  # Manually update auto_now field for bulk_update
            holdings_to_update.append(holding)
        else:
            # Fallback if no NAV found (matches original except logic)
            if not holding.current_nav:
                holding.current_nav = Decimal(0)
                holding.current_value = Decimal(0)
            # Original code did not save here, so we don't add to holdings_to_update

        invested_value = holding.units * holding.average_cost

        total_current_value += holding.current_value if holding.current_value else Decimal(0)
        total_invested_value += invested_value

        gain_loss = (holding.current_value - invested_value) if holding.current_value else Decimal(0)

        # Avoid division by zero
        if invested_value > 0:
            gain_loss_percent = (gain_loss / invested_value) * 100
        else:
            gain_loss_percent = Decimal(0)

        holdings_data.append({
            'id': holding.id,
            'scheme_name': scheme.name,
            'folio': holding.folio_number,
            'units': round(float(holding.units), 2),
            'average_cost': round(float(holding.average_cost), 2),
            'current_nav': round(float(holding.current_nav) if holding.current_nav else 0.0, 2),
            'current_value': round(float(holding.current_value) if holding.current_value else 0.0, 2),
            'invested_value': round(float(invested_value), 2),
            'gain_loss': round(float(gain_loss), 2),
            'gain_loss_percent': round(float(gain_loss_percent), 2),
            'nav_date': str(nav_date) if nav_date else None
        })

    if holdings_to_update:
        Holding.objects.bulk_update(holdings_to_update, ['current_nav', 'current_value', 'last_updated'])

    summary = {
        'total_current_value': total_current_value,
        'total_invested_value': total_invested_value,
        'total_gain_loss': total_current_value - total_invested_value,
        'holdings': holdings_data
    }

    return summary
