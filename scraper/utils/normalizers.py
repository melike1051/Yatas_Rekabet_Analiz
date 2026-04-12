from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


def parse_price(price_text: str | None) -> Decimal | None:
    if not price_text:
        return None

    normalized = (
        price_text.replace("TL", "")
        .replace("₺", "")
        .replace("\xa0", "")
        .replace(".", "")
        .replace(",", ".")
        .strip()
    )
    normalized = re.sub(r"[^0-9.]", "", normalized)
    if not normalized:
        return None

    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


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


def dump_json(path: str | Path, payload: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
