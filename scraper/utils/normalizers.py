from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


def parse_price(price_text: str | None) -> Decimal | None:
    if not price_text:
        return None

    cleaned = (
        price_text.replace("TL", "")
        .replace("₺", "")
        .replace("\xa0", "")
        .strip()
    )
    cleaned = re.sub(r"[^0-9.,]", "", cleaned)
    if not cleaned:
        return None

    normalized = _normalize_numeric_string(cleaned)
    if not normalized:
        return None

    try:
        return Decimal(normalized).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _normalize_numeric_string(value: str) -> str | None:
    if "," in value and "." in value:
        # Use the last separator as decimal separator and strip the other one.
        if value.rfind(",") > value.rfind("."):
            return value.replace(".", "").replace(",", ".")
        return value.replace(",", "")

    if "," in value:
        left, right = value.rsplit(",", 1)
        if len(right) in {1, 2}:
            return left.replace(",", "") + "." + right
        return value.replace(",", "")

    if "." in value:
        parts = value.split(".")
        if len(parts) == 2:
            left, right = parts
            if len(right) == 3:
                return left + right
            return left + "." + right

        if all(len(part) == 3 for part in parts[1:]):
            return "".join(parts)

        return "".join(parts[:-1]) + "." + parts[-1]

    return value


def parse_discount_rate(current_price: Decimal | None, original_price: Decimal | None) -> Decimal | None:
    if not current_price or not original_price or original_price == 0:
        return None
    return ((original_price - current_price) / original_price * 100).quantize(Decimal("0.01"))


def infer_stock_state(stock_text: str | None) -> bool | None:
    if not stock_text:
        return None

    text = stock_text.lower()
    if any(keyword in text for keyword in ["stokta yok", "tukendi", "gelince haber ver"]):
        return False
    if any(keyword in text for keyword in ["stokta", "hemen teslim", "sepete ekle"]):
        return True
    return None


def make_json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: make_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [make_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [make_json_safe(item) for item in value]
    return value


def dump_json(path: str | Path, payload: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(make_json_safe(payload), indent=2, ensure_ascii=False), encoding="utf-8")
