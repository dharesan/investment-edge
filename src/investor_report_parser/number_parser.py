from __future__ import annotations

from decimal import Decimal


def is_numeric_token(token: str) -> bool:
    cleaned = token.strip()
    if not cleaned:
        return False
    if cleaned in {"-", "*"}:
        return True
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = cleaned[1:-1]
    cleaned = cleaned.replace(",", "").replace("$", "").replace("%", "")
    try:
        Decimal(cleaned)
    except Exception:
        return False
    return True


def parse_numeric_token(token: str):
    cleaned = token.strip()
    if cleaned in {"", "-"}:
        return None
    if cleaned == "*":
        return "*"
    is_negative = cleaned.startswith("(") and cleaned.endswith(")")
    if is_negative:
        cleaned = cleaned[1:-1]
    cleaned = cleaned.replace(",", "").replace("$", "")
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]
        value = Decimal(cleaned) / Decimal(100)
        return float(-value if is_negative else value)
    if cleaned == "":
        return None
    if "." in cleaned:
        try:
            value = float(cleaned)
        except ValueError:
            return None
    else:
        try:
            value = int(cleaned)
        except ValueError:
            return None
    return -value if is_negative else value


def format_number_for_excel(value):
    if value is None or value == "*":
        return value
    return value
