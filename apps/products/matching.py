from dataclasses import dataclass
from typing import Optional
from .models import Scheme


def normalize_name(name: str) -> str:
    return (
        name.lower()
        .replace("direct", "")
        .replace("regular", "")
        .replace("growth", "")
        .replace("idcw", "")
        .replace("-", " ")
        .strip()
    )


@dataclass
class SchemeRecord:
    name: str
    isin: Optional[str] = None
    amfi_code: Optional[str] = None
    plan_type: Optional[str] = None
    option: Optional[str] = None


def match_scheme(record: SchemeRecord) -> Optional[Scheme]:
    if record.isin:
        match = Scheme.objects.filter(isin=record.isin).first()
        if match:
            return match

    return Scheme.objects.filter(
        normalized_name=normalize_name(record.name)
    ).first()
