from __future__ import annotations

import json
import re
from decimal import Decimal
from os import getenv
from typing import Optional

from llm_processor.client import LLMClientError, call_openai_compatible
from llm_processor.prompt_templates import build_product_spec_prompt
from llm_processor.schemas import ExtractedProductSpec, ProductSpecCandidate
from scraper.utils.logging_config import get_logger


MATERIAL_PATTERNS = {
    "MDF": r"\bmdf\b",
    "Suntalam": r"\bsuntalam\b",
    "HighGloss": r"\bhigh\s*gloss\b|\bhighgloss\b",
    "Lake": r"\blake\b",
    "Masif Ahsap": r"\bmasif\b|\bahsap\b",
    "Metal": r"\bmetal\b",
    "Cam": r"\bcam\b|\bglass\b",
}

SKELETON_PATTERNS = {
    "Metal Ayak": r"\bmetal ayak\b",
    "Ahsap Ayak": r"\bahsap ayak\b|\btahta ayak\b",
    "X Ayak": r"\bx ayak\b",
    "Konik Ayak": r"\bkonik ayak\b",
}

COLOR_PATTERNS = [
    "beyaz",
    "ceviz",
    "antrasit",
    "meşe",
    "meşe",
    "siyah",
    "krem",
    "gri",
    "vizon",
]

logger = get_logger("llm_processor.extractor")


def _to_decimal(value: str) -> Optional[Decimal]:
    try:
        return Decimal(value.replace(",", "."))
    except Exception:
        return None


def _normalize_optional_decimal(value: object) -> Optional[Decimal]:
    if value in {None, ""}:
        return None
    return _to_decimal(str(value))


def parse_llm_json_response(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    return json.loads(cleaned)


def build_spec_from_llm_payload(payload: dict) -> ExtractedProductSpec:
    return ExtractedProductSpec(
        material_type=payload.get("material_type"),
        tabletop_thickness_mm=_normalize_optional_decimal(payload.get("tabletop_thickness_mm")),
        width_cm=_normalize_optional_decimal(payload.get("width_cm")),
        depth_cm=_normalize_optional_decimal(payload.get("depth_cm")),
        height_cm=_normalize_optional_decimal(payload.get("height_cm")),
        skeleton_type=payload.get("skeleton_type"),
        color=payload.get("color"),
        parsed_by="llm",
        confidence_score=_normalize_optional_decimal(payload.get("confidence_score")),
        spec_payload={"source": "llm", "raw_payload": payload},
    )


def merge_specs(primary: ExtractedProductSpec, fallback: ExtractedProductSpec) -> ExtractedProductSpec:
    return ExtractedProductSpec(
        material_type=primary.material_type or fallback.material_type,
        tabletop_thickness_mm=primary.tabletop_thickness_mm or fallback.tabletop_thickness_mm,
        width_cm=primary.width_cm or fallback.width_cm,
        depth_cm=primary.depth_cm or fallback.depth_cm,
        height_cm=primary.height_cm or fallback.height_cm,
        skeleton_type=primary.skeleton_type or fallback.skeleton_type,
        color=primary.color or fallback.color,
        parsed_by=primary.parsed_by,
        confidence_score=primary.confidence_score or fallback.confidence_score,
        spec_payload={
            "source": primary.parsed_by,
            "primary": primary.spec_payload or {},
            "fallback": fallback.spec_payload or {},
        },
    )


def _match_measurement(pattern: str, text: str) -> Optional[Decimal]:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return _to_decimal(match.group(1))


def extract_specs_heuristic(candidate: ProductSpecCandidate) -> ExtractedProductSpec:
    text = candidate.source_text.lower()
    material_type = next((name for name, pattern in MATERIAL_PATTERNS.items() if re.search(pattern, text)), None)
    skeleton_type = next((name for name, pattern in SKELETON_PATTERNS.items() if re.search(pattern, text)), None)
    color = next((name for name in COLOR_PATTERNS if name in text), None)

    width_cm = _match_measurement(r"\bgeni[sş]lik[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*cm\b", text)
    depth_cm = _match_measurement(r"\bderinlik[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*cm\b", text)
    height_cm = _match_measurement(r"\by[üu]kseklik[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*cm\b", text)
    tabletop_thickness_mm = _match_measurement(
        r"\b(?:tabla kal[ıi]nl[ıi][gğ][ıi]|kal[ıi]nl[ıi]k)[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*mm\b",
        text,
    )

    identified_fields = [
        value
        for value in [material_type, skeleton_type, color, width_cm, depth_cm, height_cm, tabletop_thickness_mm]
        if value is not None
    ]
    confidence = Decimal("0.250")
    if identified_fields:
        confidence = min(Decimal("0.250") + Decimal("0.100") * len(identified_fields), Decimal("0.850"))

    return ExtractedProductSpec(
        material_type=material_type,
        tabletop_thickness_mm=tabletop_thickness_mm,
        width_cm=width_cm,
        depth_cm=depth_cm,
        height_cm=height_cm,
        skeleton_type=skeleton_type,
        color=color,
        parsed_by="heuristic",
        confidence_score=confidence,
        spec_payload={
            "source": "heuristic",
            "source_text": candidate.source_text,
            "identified_fields": len(identified_fields),
        },
    )


def extract_specs(candidate: ProductSpecCandidate) -> ExtractedProductSpec:
    heuristic_spec = extract_specs_heuristic(candidate)
    provider = getenv("LLM_PROVIDER", "heuristic").lower()
    if provider in {"heuristic", "", "none"}:
        return heuristic_spec

    if provider == "openai_compatible":
        try:
            prompt = build_product_spec_prompt(candidate.source_text)
            response_text = call_openai_compatible(prompt)
            llm_payload = parse_llm_json_response(response_text)
            llm_spec = build_spec_from_llm_payload(llm_payload)
            return merge_specs(llm_spec, heuristic_spec)
        except (LLMClientError, json.JSONDecodeError) as exc:
            logger.warning(
                "LLM extraction failed, heuristic fallback will be used",
                extra={
                    "extra_fields": {
                        "competitor_name": candidate.competitor_name,
                        "competitor_sku": candidate.competitor_sku,
                    }
                },
                exc_info=exc,
            )
            return heuristic_spec

    logger.warning(
        "Unsupported LLM provider configured, heuristic fallback will be used",
        extra={"extra_fields": {"provider": provider}},
    )
    return heuristic_spec
