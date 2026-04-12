from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

from db.session import engine
from scraper.utils.logging_config import get_logger
from scraper.utils.normalizers import dump_json


logger = get_logger("analysis.executive_summary")


def build_price_change_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    increased = [row for row in rows if row["price_change"] > 0]
    decreased = [row for row in rows if row["price_change"] < 0]
    unchanged = [row for row in rows if row["price_change"] == 0]

    brand_discount_counts: dict[str, int] = {}
    for row in decreased:
        brand_discount_counts[row["competitor_name"]] = brand_discount_counts.get(row["competitor_name"], 0) + 1

    top_discount_brand = None
    if brand_discount_counts:
        top_discount_brand = max(brand_discount_counts.items(), key=lambda item: item[1])[0]

    return {
        "changed_product_count": len(rows),
        "price_increased_count": len(increased),
        "price_decreased_count": len(decreased),
        "price_unchanged_count": len(unchanged),
        "top_discount_brand": top_discount_brand,
    }


def _read_catalog_diff_summary() -> dict[str, Any] | None:
    path = Path("analysis/data/catalog_diff_summary.json")
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def generate_executive_summary() -> dict[str, Any]:
    with engine.connect() as connection:
        overview = connection.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM competitors WHERE is_active = TRUE) AS competitor_count,
                    (SELECT COUNT(*) FROM products) AS product_count,
                    (SELECT COUNT(*) FROM promotions WHERE captured_at >= NOW() - INTERVAL '7 day') AS weekly_promotion_count,
                    (SELECT COUNT(*) FROM products WHERE in_stock = FALSE) AS out_of_stock_count
                """
            )
        ).mappings().one()

        latest_prices = connection.execute(
            text(
                """
                WITH ranked_prices AS (
                    SELECT
                        c.name AS competitor_name,
                        p.product_name,
                        p.competitor_sku,
                        ph.price,
                        ph.captured_at,
                        LAG(ph.price) OVER (
                            PARTITION BY ph.product_id
                            ORDER BY ph.captured_at DESC
                        ) AS previous_price,
                        ROW_NUMBER() OVER (
                            PARTITION BY ph.product_id
                            ORDER BY ph.captured_at DESC
                        ) AS row_num
                    FROM price_history ph
                    JOIN products p ON p.id = ph.product_id
                    JOIN competitors c ON c.id = p.competitor_id
                )
                SELECT
                    competitor_name,
                    product_name,
                    competitor_sku,
                    price AS current_price,
                    previous_price,
                    price - previous_price AS price_change,
                    captured_at
                FROM ranked_prices
                WHERE row_num = 1 AND previous_price IS NOT NULL
                ORDER BY ABS(price - previous_price) DESC
                LIMIT 25
                """
            )
        ).mappings().all()

        latest_promotions = connection.execute(
            text(
                """
                SELECT c.name AS competitor_name, COUNT(*) AS promotion_count
                FROM promotions pr
                JOIN competitors c ON c.id = pr.competitor_id
                WHERE pr.captured_at >= NOW() - INTERVAL '7 day'
                GROUP BY c.name
                ORDER BY promotion_count DESC, c.name
                """
            )
        ).mappings().all()

        latest_stock = connection.execute(
            text(
                """
                SELECT c.name AS competitor_name, COUNT(*) AS out_of_stock_count
                FROM products p
                JOIN competitors c ON c.id = p.competitor_id
                WHERE p.in_stock = FALSE
                GROUP BY c.name
                ORDER BY out_of_stock_count DESC, c.name
                """
            )
        ).mappings().all()

    price_summary = build_price_change_summary([dict(row) for row in latest_prices])
    catalog_diff_summary = _read_catalog_diff_summary()

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overview": dict(overview),
        "price_summary": price_summary,
        "latest_price_changes": [dict(row) for row in latest_prices],
        "latest_promotions": [dict(row) for row in latest_promotions],
        "stock_summary": [dict(row) for row in latest_stock],
        "catalog_diff_summary": catalog_diff_summary,
    }
    dump_json("analysis/data/executive_summary.json", payload)
    logger.info(
        "Executive summary generated",
        extra={
            "extra_fields": {
                "product_count": payload["overview"]["product_count"],
                "weekly_promotion_count": payload["overview"]["weekly_promotion_count"],
            }
        },
    )
    return payload
