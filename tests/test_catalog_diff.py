from analysis.catalog_diff import build_catalog_diff


def test_build_catalog_diff_detects_new_and_removed_products() -> None:
    previous_items = [
        {"competitor_sku": "SKU-1", "product_name": "Urun 1"},
        {"competitor_sku": "SKU-2", "product_name": "Urun 2"},
    ]
    current_items = [
        {"competitor_sku": "SKU-2", "product_name": "Urun 2"},
        {"competitor_sku": "SKU-3", "product_name": "Urun 3"},
    ]

    result = build_catalog_diff(previous_items, current_items)

    assert result["summary"]["previous_count"] == 2
    assert result["summary"]["current_count"] == 2
    assert result["summary"]["new_count"] == 1
    assert result["summary"]["removed_count"] == 1
    assert result["summary"]["unchanged_count"] == 1
    assert result["new_products"][0]["competitor_sku"] == "SKU-3"
    assert result["removed_products"][0]["competitor_sku"] == "SKU-1"
