from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class ProductPayload(BaseModel):
    competitor_name: str
    competitor_sku: str
    product_name: str
    category_name: Optional[str] = None
    product_url: Optional[str] = None
    image_url: Optional[str] = None
    currency_code: str = "TRY"
    current_price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    discount_rate: Optional[Decimal] = None
    in_stock: Optional[bool] = None
    promotion_label: Optional[str] = None
    raw_attributes: dict = Field(default_factory=dict)
    raw_payload: dict = Field(default_factory=dict)
    captured_at: Optional[datetime] = None


class ProductSpecPayload(BaseModel):
    material_type: Optional[str] = None
    tabletop_thickness_mm: Optional[Decimal] = None
    width_cm: Optional[Decimal] = None
    depth_cm: Optional[Decimal] = None
    height_cm: Optional[Decimal] = None
    skeleton_type: Optional[str] = None
    color: Optional[str] = None
    parsed_by: str = "manual"
    confidence_score: Optional[Decimal] = None
    spec_payload: dict = Field(default_factory=dict)


class PromotionPayload(BaseModel):
    competitor_name: str
    title: str
    description: Optional[str] = None
    promotion_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    product_sku: Optional[str] = None
    raw_payload: dict = Field(default_factory=dict)


class CatalogSnapshotPayload(BaseModel):
    competitor_name: str
    snapshot_date: datetime
    category_name: Optional[str] = None
    snapshot_payload: dict
