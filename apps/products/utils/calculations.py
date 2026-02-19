from datetime import timedelta
from django.utils import timezone
from ..models import NAVHistory, Scheme
import math

def calculate_cagr(start_value, end_value, years):
    """
    Calculates Compound Annual Growth Rate.
    Formula: (End Value / Start Value) ^ (1 / n) - 1
    """
    if start_value <= 0 or years <= 0:
        return None
    try:
        return ((end_value / start_value) ** (1 / years)) - 1
    except (ValueError, ZeroDivisionError):
        return None

def get_scheme_returns(scheme):
    """
    Calculates 1Y, 3Y, 5Y returns (CAGR) for the given scheme.
    Returns a dictionary with keys '1Y', '3Y', '5Y'.
    """
    # Get latest NAV
    latest_nav_obj = scheme.nav_history.order_by('-nav_date').first()
    if not latest_nav_obj:
        return {'1Y': None, '3Y': None, '5Y': None}

    latest_nav = float(latest_nav_obj.net_asset_value)
    latest_date = latest_nav_obj.nav_date

    returns = {}
    periods = {'1Y': 1, '3Y': 3, '5Y': 5}

    for label, years in periods.items():
        target_date = latest_date - timedelta(days=365 * years)

        # Find NAV closest to target_date (looking backwards)
        # We allow a small window (e.g., look back up to 14 days if exact date is holiday)
        past_nav_obj = scheme.nav_history.filter(
            nav_date__lte=target_date,
            nav_date__gt=target_date - timedelta(days=14)
        ).order_by('-nav_date').first()

        if past_nav_obj:
             past_nav = float(past_nav_obj.net_asset_value)
             cagr = calculate_cagr(past_nav, latest_nav, years)
             returns[label] = round(cagr * 100, 2) if cagr is not None else None
        else:
             returns[label] = None

    return returns

def get_peer_comparison(scheme, limit=3):
    """
    Finds peer schemes in the same category and compares returns.
    Returns a list of dicts.
    """
    comparison_data = []

    # 1. Add Current Scheme
    scheme_returns = get_scheme_returns(scheme)
    comparison_data.append({
        'id': scheme.id,
        'name': scheme.name,
        'is_current': True,
        'aum': scheme.aum,
        'expense_ratio': scheme.expense_ratio,
        'returns_1y': scheme_returns['1Y'],
        'returns_3y': scheme_returns['3Y'],
        'returns_5y': scheme_returns['5Y'],
    })

    if not scheme.category:
        return comparison_data

    # 2. Find Peers (Same Category, Highest AUM)
    # Exclude current scheme
    peers = Scheme.objects.filter(
        category=scheme.category
    ).exclude(id=scheme.id).order_by('-aum')[:limit]

    for peer in peers:
        peer_returns = get_scheme_returns(peer)
        comparison_data.append({
            'id': peer.id,
            'name': peer.name,
            'is_current': False,
            'aum': peer.aum,
            'expense_ratio': peer.expense_ratio,
            'returns_1y': peer_returns['1Y'],
            'returns_3y': peer_returns['3Y'],
            'returns_5y': peer_returns['5Y'],
        })

    return comparison_data
