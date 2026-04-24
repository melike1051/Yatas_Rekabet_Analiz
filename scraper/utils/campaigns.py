from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


KEYWORDS = ("indirim", "kampanya", "sepette", "taksit", "faizsiz", "ekstra", "firsat")
BANNED_EXACT_MESSAGES = {
    "kampanyalar",
    "kampanya sayfasi",
    "bellona kampanya sayfasi",
    "istikbal kampanya sayfasi",
    "dogtas kampanya sayfasi",
}
BANNED_PARTIAL_MESSAGES = (
    "e-posta adresinizi girerek",
    "en yeni ürünler, kampanyalar ve avantajlardan haberdar olun",
)


def normalize_campaign_text(text: str | None) -> str:
    return " ".join(str(text or "").split()).strip()


def is_campaign_line(text: str | None) -> bool:
    normalized = normalize_campaign_text(text).casefold()
    return len(normalized) >= 8 and any(keyword in normalized for keyword in KEYWORDS)


def is_meaningful_campaign_message(message: str | None, promotion_type: str | None = None) -> bool:
    normalized = normalize_campaign_text(message)
    lowered = normalized.casefold()
    if not normalized:
        return False
    if lowered in BANNED_EXACT_MESSAGES:
        return False
    if any(partial in lowered for partial in BANNED_PARTIAL_MESSAGES):
        return False
    if promotion_type in {"basket_discount", "rate_discount", "amount_discount", "installment", "financing"}:
        return True
    if any(token in lowered for token in ("%", "taksit", "sepette", "faizsiz", "vade", "tl", "fonu")):
        return True
    if (
        ("kampanya" in lowered or "indirim" in lowered)
        and len(normalized.split()) >= 2
        and lowered not in BANNED_EXACT_MESSAGES
    ):
        return True
    return len(normalized.split()) >= 5


def classify_campaign_message(message: str | None) -> dict[str, Any]:
    normalized = normalize_campaign_text(message)
    lowered = normalized.casefold()
    result: dict[str, Any] = {
        "normalized_message": normalized,
        "promotion_type": "generic_campaign",
        "discount_value": None,
        "discount_unit": None,
        "installment_months": None,
        "campaign_scope": "general",
    }

    if not normalized:
        return result

    if "sepette" in lowered:
        result["campaign_scope"] = "basket"

    installment_match = re.search(r"(\d{1,2})\s*(?:ay\s*)?taksit", lowered)
    if installment_match:
        result["promotion_type"] = "installment"
        result["installment_months"] = int(installment_match.group(1))
        result["discount_value"] = Decimal(installment_match.group(1))
        result["discount_unit"] = "month"
        if "faizsiz" in lowered:
            result["campaign_scope"] = "financing"
        return result

    amount_match = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*tl", lowered)
    percent_match = re.search(r"%\s*([0-9]+(?:[.,][0-9]+)?)", lowered)
    if not percent_match:
        percent_match = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*%\s*(?:e\s*varan|ekstra|indirim)?", lowered)

    if "sepette" in lowered and percent_match:
        result["promotion_type"] = "basket_discount"
        result["discount_value"] = Decimal(percent_match.group(1).replace(",", "."))
        result["discount_unit"] = "percent"
        return result

    if amount_match and "indirim" in lowered:
        result["promotion_type"] = "amount_discount"
        result["discount_value"] = Decimal(amount_match.group(1).replace(",", "."))
        result["discount_unit"] = "TRY"
        return result

    if percent_match:
        result["promotion_type"] = "rate_discount"
        result["discount_value"] = Decimal(percent_match.group(1).replace(",", "."))
        result["discount_unit"] = "percent"
        return result

    if "faizsiz" in lowered:
        result["promotion_type"] = "financing"
        result["campaign_scope"] = "financing"
        return result

    return result
