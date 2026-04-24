from decimal import Decimal

from analysis.executive_summary import build_price_change_summary, build_promotion_summary


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


def test_build_promotion_summary_groups_by_brand_and_type() -> None:
    rows = [
        {
            "competitor_name": "bellona",
            "promotion_type": "basket_discount",
            "promotion_message": "Sepette %10 indirim",
            "discount_value": Decimal("10"),
            "discount_unit": "percent",
        },
        {
            "competitor_name": "bellona",
            "promotion_type": "installment",
            "promotion_message": "12 taksit",
            "discount_value": Decimal("12"),
            "discount_unit": "month",
        },
        {
            "competitor_name": "dogtas",
            "promotion_type": "rate_discount",
            "promotion_message": "%35'e varan indirim",
            "discount_value": Decimal("35"),
            "discount_unit": "percent",
        },
    ]

    result = build_promotion_summary(rows)

    assert result["top_campaign_type"] in {"basket_discount", "installment", "rate_discount"}
    assert result["brands"][0]["competitor_name"] == "bellona"
    assert result["brands"][0]["basket_discount_count"] == 1
    assert result["brands"][0]["installment_count"] == 1
    assert "Sepette %10 indirim" in result["sample_messages"]
