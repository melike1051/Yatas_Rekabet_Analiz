from __future__ import annotations

import json
from os import getenv
from typing import Any

from llm_processor.client import LLMClientError, call_openai_compatible
from llm_processor.extractor import parse_llm_json_response
from llm_processor.prompt_templates import build_competitive_insight_prompt
from scraper.utils.logging_config import get_logger


logger = get_logger("llm_processor.insights")


def _build_heuristic_insights(context: dict[str, Any]) -> dict[str, Any]:
    price_summary = context.get("price_summary", {})
    promotion_summary = context.get("promotion_summary", {})
    catalog_diff_summary = (context.get("catalog_diff_summary") or {}).get("brands", {})

    promotion_brands = promotion_summary.get("brands", [])
    top_promo_brand = promotion_brands[0] if promotion_brands else {}
    top_discount_brand = price_summary.get("top_discount_brand") or "veri yok"
    price_decreased_count = price_summary.get("price_decreased_count", 0)

    launch_lines = []
    total_new = 0
    total_removed = 0
    for brand, payload in catalog_diff_summary.items():
        summary_block = payload.get("summary", {})
        new_count = int(summary_block.get("new_count", 0) or 0)
        removed_count = int(summary_block.get("removed_count", 0) or 0)
        total_new += new_count
        total_removed += removed_count
        if new_count or removed_count:
            launch_lines.append(f"{brand}: +{new_count} yeni / -{removed_count} delist")

    campaign_insight = "Son 7 gunde anlamli kampanya mesaji siniflandirilamadi."
    if top_promo_brand:
        campaign_insight = (
            f"{top_promo_brand.get('competitor_name', 'veri yok')} kampanya tarafinda one cikiyor; "
            f"toplam {top_promo_brand.get('promotion_count', 0)} mesajin "
            f"{top_promo_brand.get('basket_discount_count', 0)} adedi sepette indirim odakli."
        )

    launch_delist_insight = (
        "Haftalik katalog hareketi sakin."
        if not launch_lines
        else f"Haftalik katalog hareketi: {'; '.join(launch_lines[:3])}."
    )

    pricing_insight = (
        f"Fiyat baskisi {top_discount_brand} tarafinda yogunlasiyor; "
        f"{price_decreased_count} urunde fiyat dususu izlendi."
    )
    strategic_summary = (
        f"Toplam {total_new} yeni urun, {total_removed} delist ve "
        f"{promotion_summary.get('top_campaign_type') or 'genel kampanya'} agirlikli mesajlar, "
        "rakiplerin hem kampanya hem katalog tarafinda aktif oldugunu gosteriyor."
    )
    recommended_actions = [
        f"{top_discount_brand} icin fiyat savunma ve karsilik stratejisi hazirlanmali.",
        "Sepette indirim mesajlari yuksek markalar icin checkout deneyimi ve kampanya dili benchmark edilmeli.",
        "Yeni urun ve delist hareketi olan takimlarda portfoy bosluklari haftalik gozden gecirilmeli.",
    ]
    return {
        "campaign_insight": campaign_insight,
        "launch_delist_insight": launch_delist_insight,
        "pricing_insight": pricing_insight,
        "strategic_summary": strategic_summary,
        "recommended_actions": recommended_actions,
        "generated_by": "heuristic",
    }


def generate_competitive_insights(context: dict[str, Any]) -> dict[str, Any]:
    provider = str(context.get("llm_provider") or "").lower()
    if provider != "openai_compatible":
        return _build_heuristic_insights(context)

    primary_model = getenv("LLM_MODEL", "")
    fallback_model = getenv("LLM_INSIGHTS_FALLBACK_MODEL", "gemini-2.5-flash")
    try:
        prompt = build_competitive_insight_prompt(context)
        response_text = call_openai_compatible(prompt, model_override=primary_model or None)
        payload = parse_llm_json_response(response_text)
        result = {
            "campaign_insight": payload.get("campaign_insight") or "",
            "launch_delist_insight": payload.get("launch_delist_insight") or "",
            "pricing_insight": payload.get("pricing_insight") or "",
            "strategic_summary": payload.get("strategic_summary") or "",
            "recommended_actions": payload.get("recommended_actions") or [],
            "generated_by": "llm",
        }
        if not isinstance(result["recommended_actions"], list):
            result["recommended_actions"] = []
        return result
    except (LLMClientError, json.JSONDecodeError) as exc:
        if isinstance(exc, LLMClientError) and "429" in str(exc) and fallback_model and fallback_model != primary_model:
            try:
                prompt = build_competitive_insight_prompt(context)
                response_text = call_openai_compatible(prompt, model_override=fallback_model)
                payload = parse_llm_json_response(response_text)
                result = {
                    "campaign_insight": payload.get("campaign_insight") or "",
                    "launch_delist_insight": payload.get("launch_delist_insight") or "",
                    "pricing_insight": payload.get("pricing_insight") or "",
                    "strategic_summary": payload.get("strategic_summary") or "",
                    "recommended_actions": payload.get("recommended_actions") or [],
                    "generated_by": f"llm:{fallback_model}",
                }
                if not isinstance(result["recommended_actions"], list):
                    result["recommended_actions"] = []
                return result
            except (LLMClientError, json.JSONDecodeError):
                logger.warning("Fallback insight model also failed, heuristic fallback will be used", exc_info=True)
        logger.warning(
            "Competitive insight generation failed, heuristic fallback will be used",
            exc_info=exc,
        )
        return _build_heuristic_insights(context)
