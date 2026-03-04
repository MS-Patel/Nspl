import pytest
import pandas as pd
from datetime import date
from apps.users.utils.parsers import parse_date

def test_parse_date_nat():
    assert parse_date(pd.NaT) is None
    assert parse_date('NaT') is None
    assert parse_date('nan') is None
    assert parse_date('') is None

def test_parse_date_valid():
    d = parse_date('15-08-2023')
    assert d == date(2023, 8, 15)

def test_parse_date_invalid_string():
    assert parse_date('invalid') is None
