from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class ScrapedProduct(BaseModel):
    competitor_name: str
    competitor_sku: str
    product_name: str
    category_name: str
    product_url: str
    current_price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    discount_rate: Optional[Decimal] = None
    in_stock: Optional[bool] = None
    promotion_label: Optional[str] = None
    raw_attributes: dict = Field(default_factory=dict)
    raw_payload: dict = Field(default_factory=dict)


class ScrapedPromotion(BaseModel):
    competitor_name: str
    title: str
    description: Optional[str] = None
    promotion_type: Optional[str] = None
    product_sku: Optional[str] = None
    raw_payload: dict = Field(default_factory=dict)
