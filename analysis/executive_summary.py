from __future__ import annotations

import json
from datetime import datetime, timezone
from os import getenv
from pathlib import Path
from typing import Any

from sqlalchemy import text

from db.session import engine
from llm_processor.insights import generate_competitive_insights
from scraper.utils.campaigns import is_meaningful_campaign_message
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


def build_promotion_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"brands": [], "top_campaign_type": None, "sample_messages": []}

    brand_index: dict[str, dict[str, Any]] = {}
    type_counts: dict[str, int] = {}
    sample_messages: list[str] = []

    for row in rows:
        brand = str(row.get("competitor_name") or "")
        promotion_type = str(row.get("promotion_type") or "generic_campaign")
        message = str(row.get("promotion_message") or "").strip()
        if not is_meaningful_campaign_message(message, promotion_type):
            continue
        brand_payload = brand_index.setdefault(
            brand,
            {
                "competitor_name": brand,
                "promotion_count": 0,
                "basket_discount_count": 0,
                "rate_discount_count": 0,
                "installment_count": 0,
                "amount_discount_count": 0,
                "top_discount_value": None,
                "top_discount_unit": None,
                "sample_message": None,
            },
        )
        brand_payload["promotion_count"] += 1
        if promotion_type == "basket_discount":
            brand_payload["basket_discount_count"] += 1
        elif promotion_type == "rate_discount":
            brand_payload["rate_discount_count"] += 1
        elif promotion_type == "installment":
            brand_payload["installment_count"] += 1
        elif promotion_type == "amount_discount":
            brand_payload["amount_discount_count"] += 1

        type_counts[promotion_type] = type_counts.get(promotion_type, 0) + 1

        discount_value = row.get("discount_value")
        if discount_value is not None and (
            brand_payload["top_discount_value"] is None or discount_value > brand_payload["top_discount_value"]
        ):
            brand_payload["top_discount_value"] = discount_value
            brand_payload["top_discount_unit"] = row.get("discount_unit")

        if message and not brand_payload["sample_message"]:
            brand_payload["sample_message"] = message
        if message and message not in sample_messages:
            sample_messages.append(message)

    top_campaign_type = max(type_counts.items(), key=lambda item: item[1])[0] if type_counts else None
    brands = sorted(brand_index.values(), key=lambda row: (-row["promotion_count"], row["competitor_name"]))
    return {
        "brands": brands,
        "top_campaign_type": top_campaign_type,
        "sample_messages": sample_messages[:5],
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
                    (
                        SELECT COUNT(DISTINCT (competitor_id::text || '|' || COALESCE(raw_payload ->> 'normalized_message', description, title)))
                        FROM promotions
                        WHERE captured_at >= NOW() - INTERVAL '7 day'
                    ) AS weekly_promotion_count,
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
                SELECT DISTINCT ON (c.name, COALESCE(pr.raw_payload ->> 'normalized_message', pr.description, pr.title))
                    c.name AS competitor_name,
                    pr.promotion_type,
                    pr.title,
                    pr.description,
                    pr.raw_payload ->> 'normalized_message' AS promotion_message,
                    NULLIF(pr.raw_payload ->> 'discount_value', '')::numeric AS discount_value,
                    pr.raw_payload ->> 'discount_unit' AS discount_unit,
                    pr.raw_payload ->> 'campaign_scope' AS campaign_scope
                FROM promotions pr
                JOIN competitors c ON c.id = pr.competitor_id
                WHERE pr.captured_at >= NOW() - INTERVAL '7 day'
                ORDER BY c.name, COALESCE(pr.raw_payload ->> 'normalized_message', pr.description, pr.title), pr.captured_at DESC
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
    promotion_summary = build_promotion_summary([dict(row) for row in latest_promotions])
    catalog_diff_summary = _read_catalog_diff_summary()
    ai_insights = generate_competitive_insights(
        {
            "llm_provider": getenv("LLM_PROVIDER", "heuristic"),
            "overview": dict(overview),
            "price_summary": price_summary,
            "promotion_summary": promotion_summary,
            "catalog_diff_summary": catalog_diff_summary,
        }
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overview": dict(overview),
        "price_summary": price_summary,
        "latest_price_changes": [dict(row) for row in latest_prices],
        "latest_promotions": [dict(row) for row in latest_promotions],
        "promotion_summary": promotion_summary,
        "ai_insights": ai_insights,
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
