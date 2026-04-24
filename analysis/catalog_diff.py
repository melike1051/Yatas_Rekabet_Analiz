from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from db.repository import CatalogRepository, session_scope
from scraper.utils.logging_config import get_logger
from scraper.utils.normalizers import dump_json


logger = get_logger("analysis.catalog_diff")


def _item_key(item: dict[str, Any]) -> str:
    return (
        str(item.get("competitor_sku") or "").strip()
        or str(item.get("product_url") or "").strip()
        or str(item.get("product_name") or "").strip().lower()
    )


def build_catalog_diff(previous_items: list[dict[str, Any]], current_items: list[dict[str, Any]]) -> dict[str, Any]:
    previous_index = {_item_key(item): item for item in previous_items if _item_key(item)}
    current_index = {_item_key(item): item for item in current_items if _item_key(item)}

    previous_keys = set(previous_index)
    current_keys = set(current_index)

    new_keys = sorted(current_keys - previous_keys)
    removed_keys = sorted(previous_keys - current_keys)
    common_keys = sorted(previous_keys & current_keys)

    return {
        "summary": {
            "previous_count": len(previous_items),
            "current_count": len(current_items),
            "new_count": len(new_keys),
            "removed_count": len(removed_keys),
            "unchanged_count": len(common_keys),
        },
        "new_products": [current_index[key] for key in new_keys],
        "removed_products": [previous_index[key] for key in removed_keys],
        "unchanged_products": [current_index[key] for key in common_keys],
    }


def analyze_brand_catalog_diff(brand: str, category_name: str = "Yemek Odasi") -> dict[str, Any]:
    with session_scope() as session:
        repo = CatalogRepository(session)
        snapshot_pair = repo.get_latest_snapshot_pair(brand, category_name=category_name)

    if not snapshot_pair:
        result = {
            "brand": brand,
            "category_name": category_name,
            "status": "no_snapshots",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        dump_json(f"analysis/data/{brand}_catalog_diff.json", result)
        return result

    current_snapshot, previous_snapshot = snapshot_pair
    current_items = current_snapshot.get("items", [])

    if previous_snapshot is None:
        result = {
            "brand": brand,
            "category_name": category_name,
            "status": "no_previous_snapshot",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "current_snapshot_date": current_snapshot["snapshot_date"],
            "current_count": len(current_items),
        }
        dump_json(f"analysis/data/{brand}_catalog_diff.json", result)
        return result

    previous_items = previous_snapshot.get("items", [])
    diff = build_catalog_diff(previous_items, current_items)
    result = {
        "brand": brand,
        "category_name": category_name,
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "previous_snapshot_date": previous_snapshot["snapshot_date"],
        "current_snapshot_date": current_snapshot["snapshot_date"],
        **diff,
    }
    dump_json(f"analysis/data/{brand}_catalog_diff.json", result)
    logger.info(
        "Catalog diff generated",
        extra={
            "extra_fields": {
                "brand": brand,
                "new_count": result["summary"]["new_count"],
                "removed_count": result["summary"]["removed_count"],
            }
        },
    )
    return result


def analyze_all_catalog_diffs(category_name: str = "Yemek Odasi") -> dict[str, Any]:
    brands = ("istikbal", "bellona", "dogtas")
    results = {brand: analyze_brand_catalog_diff(brand, category_name=category_name) for brand in brands}
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "category_name": category_name,
        "brands": results,
    }
    dump_json("analysis/data/catalog_diff_summary.json", payload)
    return payload
