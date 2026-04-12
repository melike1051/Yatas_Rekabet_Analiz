from analysis.reporting import build_management_summary, flatten_catalog_diff_rows, parse_email_recipients


def test_parse_email_recipients_supports_comma_and_semicolon() -> None:
    recipients = parse_email_recipients("a@example.com; b@example.com, c@example.com")
    assert recipients == ["a@example.com", "b@example.com", "c@example.com"]


def test_flatten_catalog_diff_rows_builds_brand_rows() -> None:
    summary = {
        "catalog_diff_summary": {
            "brands": {
                "bellona": {
                    "status": "ok",
                    "summary": {
                        "previous_count": 10,
                        "current_count": 12,
                        "new_count": 3,
                        "removed_count": 1,
                        "unchanged_count": 8,
                    },
                }
            }
        }
    }

    rows = flatten_catalog_diff_rows(summary)

    assert rows == [
        {
            "Marka": "bellona",
            "Durum": "ok",
            "Onceki Katalog": 10,
            "Guncel Katalog": 12,
            "Yeni Urun": 3,
            "Kalkan Urun": 1,
            "Sabit Kalan": 8,
        }
    ]


def test_build_management_summary_contains_actionable_headlines() -> None:
    summary = {
        "overview": {
            "competitor_count": 3,
            "product_count": 250,
            "weekly_promotion_count": 6,
            "out_of_stock_count": 4,
        },
        "price_summary": {
            "top_discount_brand": "istikbal",
            "price_decreased_count": 12,
            "price_increased_count": 5,
        },
        "catalog_diff_summary": {
            "brands": {
                "istikbal": {"summary": {"new_count": 2, "removed_count": 1}},
                "bellona": {"summary": {"new_count": 1, "removed_count": 0}},
            }
        },
    }

    result = build_management_summary(summary)

    assert len(result) == 4
    assert "istikbal" in result[2]
    assert "3 yeni" in result[3]
