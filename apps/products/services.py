from typing import Optional
from .models import Scheme, BSESchemeMapping, NAVHistory


def get_bse_code(scheme: Scheme, txn_type: str, amount: float) -> Optional[BSESchemeMapping]:
    return (
        BSESchemeMapping.objects
        .filter(
            scheme=scheme,
            transaction_type=txn_type,
            min_amount__lte=amount
        )
        .order_by("min_amount")
        .first()
    )


def get_latest_nav(scheme: Scheme) -> Optional[NAVHistory]:
    return (
        NAVHistory.objects
        .filter(scheme=scheme)
        .order_by("-nav_date")
        .first()
    )
