CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS competitors (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    website_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    id BIGSERIAL PRIMARY KEY,
    competitor_id BIGINT NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
    competitor_sku VARCHAR(150) NOT NULL,
    product_name TEXT NOT NULL,
    category_name VARCHAR(150),
    product_url TEXT,
    currency_code CHAR(3) NOT NULL DEFAULT 'TRY',
    current_price NUMERIC(12, 2),
    in_stock BOOLEAN,
    raw_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (competitor_id, competitor_sku)
);

CREATE TABLE IF NOT EXISTS product_specs (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL UNIQUE REFERENCES products(id) ON DELETE CASCADE,
    material_type VARCHAR(100),
    tabletop_thickness_mm NUMERIC(8, 2),
    width_cm NUMERIC(8, 2),
    depth_cm NUMERIC(8, 2),
    height_cm NUMERIC(8, 2),
    skeleton_type VARCHAR(150),
    color TEXT,
    parsed_by VARCHAR(50) NOT NULL DEFAULT 'manual',
    confidence_score NUMERIC(4, 3),
    spec_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS price_history (
    id BIGSERIAL,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    price NUMERIC(12, 2) NOT NULL,
    original_price NUMERIC(12, 2),
    discount_rate NUMERIC(5, 2),
    in_stock BOOLEAN,
    promotion_label TEXT,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (id, captured_at)
);

CREATE TABLE IF NOT EXISTS promotions (
    id BIGSERIAL PRIMARY KEY,
    competitor_id BIGINT NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
    product_id BIGINT REFERENCES products(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    promotion_type VARCHAR(100),
    start_date DATE,
    end_date DATE,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS catalog_snapshots (
    id BIGSERIAL PRIMARY KEY,
    competitor_id BIGINT NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    category_name VARCHAR(150),
    snapshot_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (competitor_id, snapshot_date, category_name)
);

SELECT create_hypertable('price_history', 'captured_at', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_products_competitor_category
    ON products (competitor_id, category_name);

CREATE INDEX IF NOT EXISTS idx_product_specs_material_type
    ON product_specs (material_type);

CREATE INDEX IF NOT EXISTS idx_price_history_product_captured_at
    ON price_history (product_id, captured_at DESC);

CREATE INDEX IF NOT EXISTS idx_promotions_competitor_captured_at
    ON promotions (competitor_id, captured_at DESC);

CREATE INDEX IF NOT EXISTS idx_catalog_snapshots_competitor_snapshot_date
    ON catalog_snapshots (competitor_id, snapshot_date DESC);
