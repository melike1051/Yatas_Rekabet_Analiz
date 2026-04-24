from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, desc, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from db.models import CatalogSnapshot, Competitor, PriceHistory, Product, ProductSpec, Promotion
from db.schemas import CatalogSnapshotPayload, ProductPayload, ProductSpecPayload, PromotionPayload
from db.session import SessionLocal


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class CompetitorRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_or_create_competitor(self, name: str, website_url: Optional[str] = None) -> int:
        stmt = (
            insert(Competitor)
            .values(name=name, website_url=website_url)
            .on_conflict_do_update(
                index_elements=[Competitor.name],
                set_={"website_url": website_url, "updated_at": datetime.now(timezone.utc)},
            )
            .returning(Competitor.id)
        )
        return self.session.execute(stmt).scalar_one()


class ProductRepository:
    def __init__(self, session: Session):
        self.session = session
        self.competitors = CompetitorRepository(session)

    def upsert_product(self, payload: ProductPayload) -> int:
        competitor_id = self.competitors.get_or_create_competitor(payload.competitor_name)
        raw_attributes = dict(payload.raw_attributes or {})
        if payload.image_url:
            raw_attributes["image_url"] = payload.image_url

        stmt = (
            insert(Product)
            .values(
                competitor_id=competitor_id,
                competitor_sku=payload.competitor_sku,
                product_name=payload.product_name,
                category_name=payload.category_name,
                product_url=payload.product_url,
                currency_code=payload.currency_code,
                current_price=payload.current_price,
                in_stock=payload.in_stock,
                raw_attributes=raw_attributes,
            )
            .on_conflict_do_update(
                index_elements=[Product.competitor_id, Product.competitor_sku],
                set_={
                    "product_name": payload.product_name,
                    "category_name": payload.category_name,
                    "product_url": payload.product_url,
                    "currency_code": payload.currency_code,
                    "current_price": payload.current_price,
                    "in_stock": payload.in_stock,
                    "raw_attributes": raw_attributes,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            .returning(Product.id)
        )
        product_id = self.session.execute(stmt).scalar_one()

        if payload.current_price is not None:
            self.session.add(
                PriceHistory(
                    product_id=product_id,
                    captured_at=payload.captured_at or datetime.now(timezone.utc),
                    price=payload.current_price,
                    original_price=payload.original_price,
                    discount_rate=payload.discount_rate,
                    in_stock=payload.in_stock,
                    promotion_label=payload.promotion_label,
                    raw_payload=payload.raw_payload,
                )
            )

        return product_id

    def upsert_product_spec(self, product_id: int, payload: ProductSpecPayload) -> ProductSpec:
        stmt = (
            insert(ProductSpec)
            .values(product_id=product_id, **payload.model_dump())
            .on_conflict_do_update(
                index_elements=[ProductSpec.product_id],
                set_={**payload.model_dump(), "updated_at": datetime.now(timezone.utc)},
            )
            .returning(ProductSpec)
        )
        return self.session.execute(stmt).scalar_one()

    def get_product_by_sku(self, competitor_name: str, competitor_sku: str) -> Optional[Product]:
        stmt = (
            select(Product)
            .join(Competitor, Competitor.id == Product.competitor_id)
            .where(Competitor.name == competitor_name, Product.competitor_sku == competitor_sku)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_products_for_spec_extraction(self, limit: int = 100, include_existing: bool = False) -> list[dict]:
        stmt = (
            select(
                Product.id.label("product_id"),
                Competitor.name.label("competitor_name"),
                Product.competitor_sku,
                Product.product_name,
                Product.category_name,
                Product.product_url,
                Product.raw_attributes,
            )
            .join(Competitor, Competitor.id == Product.competitor_id)
            .outerjoin(ProductSpec, ProductSpec.product_id == Product.id)
            .order_by(Product.updated_at.desc())
            .limit(limit)
        )
        if not include_existing:
            stmt = stmt.where(ProductSpec.id.is_(None))
        return [dict(row._mapping) for row in self.session.execute(stmt).all()]

    def update_product_raw_attributes(self, product_id: int, raw_attributes: dict) -> None:
        stmt = (
            update(Product)
            .where(Product.id == product_id)
            .values(
                raw_attributes=raw_attributes,
                updated_at=datetime.now(timezone.utc),
            )
        )
        self.session.execute(stmt)


class PromotionRepository:
    def __init__(self, session: Session):
        self.session = session
        self.competitors = CompetitorRepository(session)
        self.products = ProductRepository(session)

    def create_promotion(self, payload: PromotionPayload) -> Promotion:
        competitor_id = self.competitors.get_or_create_competitor(payload.competitor_name)
        product_id = None
        if payload.product_sku:
            product = self.products.get_product_by_sku(payload.competitor_name, payload.product_sku)
            product_id = product.id if product else None

        normalized_message = (
            str((payload.raw_payload or {}).get("normalized_message") or payload.description or payload.title or "").strip()
        )
        normalized_message_expr = Promotion.raw_payload["normalized_message"].as_string()
        duplicate_stmt = (
            select(Promotion)
            .where(
                Promotion.competitor_id == competitor_id,
                Promotion.promotion_type == payload.promotion_type,
                func.coalesce(normalized_message_expr, Promotion.description, Promotion.title) == normalized_message,
                Promotion.captured_at >= func.date_trunc("day", func.now()),
            )
            .limit(1)
        )
        existing = self.session.execute(duplicate_stmt).scalar_one_or_none()
        if existing:
            return existing

        promotion = Promotion(
            competitor_id=competitor_id,
            product_id=product_id,
            title=payload.title,
            description=payload.description,
            promotion_type=payload.promotion_type,
            start_date=payload.start_date,
            end_date=payload.end_date,
            raw_payload=payload.raw_payload,
        )
        self.session.add(promotion)
        self.session.flush()
        return promotion


class CatalogRepository:
    def __init__(self, session: Session):
        self.session = session
        self.competitors = CompetitorRepository(session)

    def upsert_snapshot(self, payload: CatalogSnapshotPayload) -> int:
        competitor_id = self.competitors.get_or_create_competitor(payload.competitor_name)
        stmt = (
            insert(CatalogSnapshot)
            .values(
                competitor_id=competitor_id,
                snapshot_date=payload.snapshot_date.date(),
                category_name=payload.category_name,
                snapshot_payload=payload.snapshot_payload,
            )
            .on_conflict_do_update(
                index_elements=[
                    CatalogSnapshot.competitor_id,
                    CatalogSnapshot.snapshot_date,
                    CatalogSnapshot.category_name,
                ],
                set_={"snapshot_payload": payload.snapshot_payload},
            )
            .returning(CatalogSnapshot.id)
        )
        return self.session.execute(stmt).scalar_one()

    def get_latest_snapshot_pair(self, competitor_name: str, category_name: Optional[str] = None) -> Optional[tuple[dict, Optional[dict]]]:
        stmt = (
            select(CatalogSnapshot.snapshot_date, CatalogSnapshot.snapshot_payload)
            .join(Competitor, Competitor.id == CatalogSnapshot.competitor_id)
            .where(Competitor.name == competitor_name)
            .order_by(desc(CatalogSnapshot.snapshot_date))
            .limit(2)
        )
        if category_name:
            stmt = stmt.where(CatalogSnapshot.category_name == category_name)

        rows = self.session.execute(stmt).all()
        if not rows:
            return None

        snapshots = [
            {
                "snapshot_date": row.snapshot_date.isoformat(),
                "items": row.snapshot_payload.get("items", []) if isinstance(row.snapshot_payload, dict) else [],
            }
            for row in rows
        ]

        current_snapshot = snapshots[0]
        previous_snapshot = snapshots[1] if len(snapshots) > 1 else None
        return current_snapshot, previous_snapshot
