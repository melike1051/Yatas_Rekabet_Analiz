from analysis.executive_summary import build_price_change_summary


def test_build_price_change_summary() -> None:
    rows = [
        {"competitor_name": "istikbal", "price_change": -100},
        {"competitor_name": "istikbal", "price_change": -50},
        {"competitor_name": "bellona", "price_change": 25},
        {"competitor_name": "dogtas", "price_change": 0},
    ]

    result = build_price_change_summary(rows)

    assert result["changed_product_count"] == 4
    assert result["price_increased_count"] == 1
    assert result["price_decreased_count"] == 2
    assert result["price_unchanged_count"] == 1
    assert result["top_discount_brand"] == "istikbal"
