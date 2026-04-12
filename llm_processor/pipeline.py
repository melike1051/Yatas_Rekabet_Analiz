from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from db.repository import ProductRepository, session_scope
from db.schemas import ProductSpecPayload
from llm_processor.detail_fetcher import ProductDetailFetcher
from llm_processor.extractor import extract_specs
from llm_processor.schemas import ProductSpecCandidate
from scraper.utils.logging_config import get_logger
from scraper.utils.normalizers import dump_json


logger = get_logger("llm_processor.pipeline")


def build_source_text(product: dict) -> str:
    raw_attributes = product.get("raw_attributes") or {}
    raw_attributes_text = json.dumps(raw_attributes, ensure_ascii=False)
    return "\n".join(
        [
            f"Marka: {product.get('competitor_name', '')}",
            f"Kategori: {product.get('category_name', '')}",
            f"Urun: {product.get('product_name', '')}",
            f"SKU: {product.get('competitor_sku', '')}",
            f"Ham Alanlar: {raw_attributes_text}",
        ]
    ).strip()


async def enrich_products_with_detail_context(products: list[dict]) -> list[dict]:
    async with ProductDetailFetcher() as fetcher:
        enriched: list[dict] = []
        for product in products:
            raw_attributes = dict(product.get("raw_attributes") or {})
            product_url = product.get("product_url")
            if product_url and not raw_attributes.get("detail_context"):
                try:
                    raw_attributes["detail_context"] = await fetcher.fetch_detail_context(product_url)
                except Exception as exc:
                    logger.warning(
                        "Product detail enrichment failed",
                        extra={
                            "extra_fields": {
                                "product_id": product["product_id"],
                                "product_url": product_url,
                            }
                        },
                        exc_info=exc,
                    )
            product = dict(product)
            product["raw_attributes"] = raw_attributes
            enriched.append(product)
        return enriched


def extract_product_specs(limit: int = 100, include_existing: bool = False) -> dict:
    with session_scope() as session:
        product_repo = ProductRepository(session)
        candidates = product_repo.list_products_for_spec_extraction(limit=limit, include_existing=include_existing)
    candidates = asyncio.run(enrich_products_with_detail_context(candidates))

    with session_scope() as session:
        product_repo = ProductRepository(session)
        processed = []

        for product in candidates:
            product_repo.update_product_raw_attributes(product["product_id"], product.get("raw_attributes") or {})
            candidate = ProductSpecCandidate(
                product_id=product["product_id"],
                competitor_name=product["competitor_name"],
                competitor_sku=product["competitor_sku"],
                product_name=product["product_name"],
                category_name=product.get("category_name"),
                product_url=product.get("product_url"),
                source_text=build_source_text(product),
            )
            extracted = extract_specs(candidate)
            payload = ProductSpecPayload(
                material_type=extracted.material_type,
                tabletop_thickness_mm=extracted.tabletop_thickness_mm,
                width_cm=extracted.width_cm,
                depth_cm=extracted.depth_cm,
                height_cm=extracted.height_cm,
                skeleton_type=extracted.skeleton_type,
                color=extracted.color,
                parsed_by=extracted.parsed_by,
                confidence_score=extracted.confidence_score,
                spec_payload=extracted.spec_payload or {},
            )
            product_repo.upsert_product_spec(candidate.product_id, payload)
            processed.append(
                {
                    "product_id": candidate.product_id,
                    "competitor_name": candidate.competitor_name,
                    "competitor_sku": candidate.competitor_sku,
                    "product_name": candidate.product_name,
                    "parsed_by": extracted.parsed_by,
                    "confidence_score": str(extracted.confidence_score) if extracted.confidence_score is not None else None,
                }
            )

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "include_existing": include_existing,
        "processed_count": len(processed),
        "items": processed,
    }
    dump_json("llm_processor/data/product_specs_summary.json", result)
    logger.info(
        "Product spec extraction completed",
        extra={"extra_fields": {"processed_count": len(processed)}},
    )
    return result
