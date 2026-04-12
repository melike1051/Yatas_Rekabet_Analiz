from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from db.session import Base


class Competitor(Base):
    __tablename__ = "competitors"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    website_url = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("competitor_id", "competitor_sku", name="uq_products_competitor_sku"),)

    id = Column(Integer, primary_key=True)
    competitor_id = Column(ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False)
    competitor_sku = Column(String(150), nullable=False)
    product_name = Column(Text, nullable=False)
    category_name = Column(String(150))
    product_url = Column(Text)
    currency_code = Column(String(3), default="TRY", nullable=False)
    current_price = Column(Numeric(12, 2))
    in_stock = Column(Boolean)
    raw_attributes = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    specs = relationship("ProductSpec", back_populates="product", cascade="all, delete-orphan", uselist=False)


class ProductSpec(Base):
    __tablename__ = "product_specs"

    id = Column(Integer, primary_key=True)
    product_id = Column(ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False)
    material_type = Column(String(100))
    tabletop_thickness_mm = Column(Numeric(8, 2))
    width_cm = Column(Numeric(8, 2))
    depth_cm = Column(Numeric(8, 2))
    height_cm = Column(Numeric(8, 2))
    skeleton_type = Column(String(150))
    color = Column(Text)
    parsed_by = Column(String(50), default="manual", nullable=False)
    confidence_score = Column(Numeric(4, 3))
    spec_payload = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    product = relationship("Product", back_populates="specs")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True)
    product_id = Column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    original_price = Column(Numeric(12, 2))
    discount_rate = Column(Numeric(5, 2))
    in_stock = Column(Boolean)
    promotion_label = Column(Text)
    raw_payload = Column(JSON, default=dict, nullable=False)


class Promotion(Base):
    __tablename__ = "promotions"

    id = Column(Integer, primary_key=True)
    competitor_id = Column(ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(ForeignKey("products.id", ondelete="SET NULL"))
    title = Column(Text, nullable=False)
    description = Column(Text)
    promotion_type = Column(String(100))
    start_date = Column(Date)
    end_date = Column(Date)
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    raw_payload = Column(JSON, default=dict, nullable=False)


class CatalogSnapshot(Base):
    __tablename__ = "catalog_snapshots"
    __table_args__ = (
        UniqueConstraint("competitor_id", "snapshot_date", "category_name", name="uq_catalog_snapshot"),
    )

    id = Column(Integer, primary_key=True)
    competitor_id = Column(ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    category_name = Column(String(150))
    snapshot_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
