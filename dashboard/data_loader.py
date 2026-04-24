from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from db.session import engine

LOGGER = logging.getLogger(__name__)


def load_executive_summary() -> dict[str, Any]:
    path = Path("analysis/data/executive_summary.json")
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_latest_report_metadata() -> dict[str, Any]:
    path = Path("analysis/data/reports/latest_report.json")
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_price_trend(limit_days: int = 30) -> pd.DataFrame:
    query = text(
        """
        SELECT
            c.name AS competitor_name,
            p.product_name,
            ph.captured_at::date AS captured_date,
            ph.price
        FROM price_history ph
        JOIN products p ON p.id = ph.product_id
        JOIN competitors c ON c.id = p.competitor_id
        WHERE ph.captured_at >= NOW() - (:limit_days || ' day')::interval
        ORDER BY ph.captured_at ASC
        """
    )
    try:
        with engine.connect() as connection:
            return pd.read_sql_query(query, connection, params={"limit_days": limit_days})
    except SQLAlchemyError:
        LOGGER.exception("Price trend verisi yuklenemedi.")
        return pd.DataFrame()


def load_product_specs() -> pd.DataFrame:
    query = text(
        """
        SELECT
            p.id AS product_id,
            c.name AS competitor_name,
            p.product_name,
            p.competitor_sku,
            p.current_price,
            p.product_url,
            ps.material_type,
            ps.tabletop_thickness_mm,
            ps.width_cm,
            ps.depth_cm,
            ps.height_cm,
            ps.skeleton_type,
            ps.color,
            ps.parsed_by,
            ps.confidence_score
        FROM product_specs ps
        JOIN products p ON p.id = ps.product_id
        JOIN competitors c ON c.id = p.competitor_id
        ORDER BY c.name, p.product_name
        """
    )
    try:
        with engine.connect() as connection:
            return pd.read_sql_query(query, connection)
    except SQLAlchemyError:
        LOGGER.exception("Product specs verisi yuklenemedi.")
        return pd.DataFrame()


def load_visual_product_comparison() -> pd.DataFrame:
    query = text(
        """
        WITH latest_prices AS (
            SELECT
                ph.product_id,
                ph.price,
                ph.original_price,
                ph.discount_rate,
                ROW_NUMBER() OVER (
                    PARTITION BY ph.product_id
                    ORDER BY ph.captured_at DESC
                ) AS row_num
            FROM price_history ph
        )
        SELECT
            p.id AS product_id,
            c.name AS competitor_name,
            p.product_name,
            p.competitor_sku,
            p.product_url,
            p.current_price,
            lp.price AS latest_price,
            lp.original_price,
            lp.discount_rate,
            p.raw_attributes ->> 'image_url' AS image_url,
            p.raw_attributes ->> 'team_name' AS team_name,
            p.raw_attributes ->> 'item_type' AS item_type
        FROM products p
        JOIN competitors c ON c.id = p.competitor_id
        LEFT JOIN latest_prices lp ON lp.product_id = p.id AND lp.row_num = 1
        ORDER BY c.name, p.product_name
        """
    )
    try:
        with engine.connect() as connection:
            return pd.read_sql_query(query, connection)
    except SQLAlchemyError:
        LOGGER.exception("Resimli urun karsilastirma verisi yuklenemedi.")
        return pd.DataFrame()
