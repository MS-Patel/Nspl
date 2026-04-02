import pytest
from apps.reconciliation.utils.reconcile import get_karvy_transaction_type_and_action

def test_get_karvy_transaction_type_and_action_nct():
    """
    Test that get_karvy_transaction_type_and_action correctly handles NCT remarks
    and uses the transaction flag to determine the action.
    """
    # Test NCT with P flag -> ADD
    _, action = get_karvy_transaction_type_and_action("SIN", "NCT - CoD", "P")
    assert action == "ADD"

    # Test NCT with TI flag -> ADD
    _, action = get_karvy_transaction_type_and_action("SIN", "NCT - CoD", "TI")
    assert action == "ADD"

    # Test NCT with R flag -> SUB
    _, action = get_karvy_transaction_type_and_action("FUL", "NCT - CoD", "R")
    assert action == "SUB"

    # Test NCT with TO flag -> SUB
    _, action = get_karvy_transaction_type_and_action("FUL", "NCT - CoD", "TO")
    assert action == "SUB"

    # Test NCT with SO flag -> SUB
    _, action = get_karvy_transaction_type_and_action("SWOF", "NCT - CoD", "SO")
    assert action == "SUB"

    # Test standard fallback without NCT
    _, action = get_karvy_transaction_type_and_action("SIN", "Systematic Investment", "P")
    assert action == "ADD"

    _, action = get_karvy_transaction_type_and_action("FUL", "Redemption", "P")
    assert action == "SUB"

    _, action = get_karvy_transaction_type_and_action("UNKNOWN", "UNKNOWN DESC", "P")
    assert action is None
