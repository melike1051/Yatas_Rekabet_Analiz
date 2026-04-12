from decimal import Decimal

from scraper.utils.normalizers import infer_stock_state, parse_discount_rate, parse_price


def test_parse_price_handles_turkish_format() -> None:
    assert parse_price("15.990 TL") == Decimal("15990")
    assert parse_price("12.499,90 TL") == Decimal("12499.90")


def test_parse_discount_rate() -> None:
    assert parse_discount_rate(Decimal("800"), Decimal("1000")) == Decimal("20.00")


def test_infer_stock_state() -> None:
    assert infer_stock_state("Stokta var") is True
    assert infer_stock_state("Stokta yok") is False
