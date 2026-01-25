from decimal import Decimal
from django.db.models import Sum, F
from apps.products.models import NAVHistory
from apps.reconciliation.models import Holding

def calculate_portfolio_valuation(investor_profile):
    """
    Updates current value of holdings for an investor and returns summary.
    """
    holdings = Holding.objects.filter(investor=investor_profile)

    total_current_value = Decimal(0)
    total_invested_value = Decimal(0)

    holdings_data = []

    for holding in holdings:
        scheme = holding.scheme
        latest_nav = None
        # Fetch latest NAV
        try:
            latest_nav = NAVHistory.objects.filter(scheme=scheme).latest('nav_date')
            holding.current_nav = latest_nav.net_asset_value
            holding.current_value = holding.units * latest_nav.net_asset_value
            holding.save(update_fields=['current_nav', 'current_value', 'last_updated'])
        except NAVHistory.DoesNotExist:
            if not holding.current_nav:
                holding.current_nav = Decimal(0)
                holding.current_value = Decimal(0)

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
            'units': float(holding.units),
            'average_cost': float(holding.average_cost),
            'current_nav': float(holding.current_nav) if holding.current_nav else 0.0,
            'current_value': float(holding.current_value) if holding.current_value else 0.0,
            'invested_value': float(invested_value),
            'gain_loss': float(gain_loss),
            'gain_loss_percent': float(gain_loss_percent),
            'nav_date': str(latest_nav.nav_date) if latest_nav else None
        })

    summary = {
        'total_current_value': total_current_value,
        'total_invested_value': total_invested_value,
        'total_gain_loss': total_current_value - total_invested_value,
        'holdings': holdings_data
    }

    return summary
