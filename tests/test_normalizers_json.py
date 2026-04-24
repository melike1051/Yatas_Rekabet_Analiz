from decimal import Decimal

from scraper.utils.normalizers import make_json_safe


def test_make_json_safe_converts_decimal_recursively() -> None:
    payload = {
        "discount_value": Decimal("10.50"),
        "items": [{"score": Decimal("0.75")}],
    }

    result = make_json_safe(payload)

    assert result["discount_value"] == 10.5
    assert result["items"][0]["score"] == 0.75
