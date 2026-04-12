from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class ProductSpecCandidate:
    product_id: int
    competitor_name: str
    competitor_sku: str
    product_name: str
    category_name: Optional[str]
    product_url: Optional[str]
    source_text: str


@dataclass
class ExtractedProductSpec:
    material_type: Optional[str] = None
    tabletop_thickness_mm: Optional[Decimal] = None
    width_cm: Optional[Decimal] = None
    depth_cm: Optional[Decimal] = None
    height_cm: Optional[Decimal] = None
    skeleton_type: Optional[str] = None
    color: Optional[str] = None
    parsed_by: str = "heuristic"
    confidence_score: Optional[Decimal] = None
    spec_payload: dict | None = None
