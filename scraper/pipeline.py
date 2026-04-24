from __future__ import annotations

import asyncio
from argparse import ArgumentParser
from datetime import datetime, timezone

from scraper.utils.logging_config import get_logger
from scraper.utils.normalizers import dump_json

logger = get_logger("scraper.pipeline")
SUPPORTED_BRANDS = ("istikbal", "bellona", "dogtas")


def get_scraper_registry() -> dict[str, type]:
    from scraper.brands.bellona import BellonaScraper
    from scraper.brands.dogtas import DogtasScraper
    from scraper.brands.istikbal import IstikbalScraper

    return {
        "istikbal": IstikbalScraper,
        "bellona": BellonaScraper,
        "dogtas": DogtasScraper,
    }


async def run_daily_scrape(brand: str, persist_to_db: bool = True) -> list[dict]:
    scraper_registry = get_scraper_registry()
    scraper_cls = scraper_registry[brand]
    logger.info("Daily scrape started", extra={"extra_fields": {"brand": brand}})
    async with scraper_cls() as scraper:
        products = await scraper.scrape_daily()
        promotions = await scraper.scrape_promotions()

    dump_json(f"scraper/data/{brand}_daily.json", {"products": products, "promotions": promotions})

    if persist_to_db:
        from db.repository import ProductRepository, PromotionRepository, session_scope
        from db.schemas import ProductPayload, PromotionPayload

        with session_scope() as session:
            product_repo = ProductRepository(session)
            promotion_repo = PromotionRepository(session)

            for payload in products:
                product_repo.upsert_product(ProductPayload(**payload, captured_at=datetime.now(timezone.utc)))

            for payload in promotions:
                promotion_repo.create_promotion(PromotionPayload(**payload))

    logger.info(
        "Daily scrape stored",
        extra={
            "extra_fields": {
                "brand": brand,
                "product_count": len(products),
                "promotion_count": len(promotions),
                "persist_to_db": persist_to_db,
            }
        },
    )
    return products


async def run_catalog_scrape(brand: str, persist_to_db: bool = True) -> list[dict]:
    scraper_registry = get_scraper_registry()
    scraper_cls = scraper_registry[brand]
    logger.info("Catalog scrape started", extra={"extra_fields": {"brand": brand}})
    async with scraper_cls() as scraper:
        catalog = await scraper.scrape_catalog()

    dump_json(f"scraper/data/{brand}_catalog.json", catalog)

    if persist_to_db:
        from db.repository import CatalogRepository, session_scope
        from db.schemas import CatalogSnapshotPayload

        with session_scope() as session:
            catalog_repo = CatalogRepository(session)
            catalog_repo.upsert_snapshot(
                CatalogSnapshotPayload(
                    competitor_name=brand,
                    snapshot_date=datetime.now(timezone.utc),
                    category_name="Yemek Odasi",
                    snapshot_payload={"items": catalog},
                )
            )

    logger.info(
        "Catalog scrape stored",
        extra={"extra_fields": {"brand": brand, "catalog_count": len(catalog), "persist_to_db": persist_to_db}},
    )
    return catalog


async def run_daily_scrape_for_all_brands(persist_to_db: bool = True) -> dict[str, int]:
    results: dict[str, int] = {}
    for brand in get_scraper_registry():
        products = await run_daily_scrape(brand, persist_to_db=persist_to_db)
        results[brand] = len(products)
    return results


async def run_catalog_scrape_for_all_brands(persist_to_db: bool = True) -> dict[str, int]:
    results: dict[str, int] = {}
    for brand in get_scraper_registry():
        catalog = await run_catalog_scrape(brand, persist_to_db=persist_to_db)
        results[brand] = len(catalog)
    return results


def run_catalog_diff(brand: str) -> dict:
    from analysis.catalog_diff import analyze_brand_catalog_diff

    return analyze_brand_catalog_diff(brand)


def run_catalog_diff_for_all_brands() -> dict:
    from analysis.catalog_diff import analyze_all_catalog_diffs

    return analyze_all_catalog_diffs()


def run_executive_summary() -> dict:
    from analysis.executive_summary import generate_executive_summary

    return generate_executive_summary()


def run_product_spec_extraction(limit: int = 100, include_existing: bool = False) -> dict:
    from llm_processor.pipeline import extract_product_specs

    return extract_product_specs(limit=limit, include_existing=include_existing)


def run_weekly_report_generation(send_email: bool = False) -> dict:
    from analysis.reporting import generate_weekly_report

    return generate_weekly_report(send_email=send_email)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Competitor scraping pipeline")
    parser.add_argument("mode", choices=["daily", "catalog", "diff", "summary", "specs", "report"])
    parser.add_argument("--brand", choices=sorted(SUPPORTED_BRANDS))
    parser.add_argument("--skip-db", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--refresh-specs", action="store_true")
    parser.add_argument("--email-report", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    persist_to_db = not args.skip_db
    if args.mode == "daily":
        if args.brand:
            asyncio.run(run_daily_scrape(args.brand, persist_to_db=persist_to_db))
        else:
            asyncio.run(run_daily_scrape_for_all_brands(persist_to_db=persist_to_db))
        return

    if args.mode == "catalog":
        if args.brand:
            asyncio.run(run_catalog_scrape(args.brand, persist_to_db=persist_to_db))
        else:
            asyncio.run(run_catalog_scrape_for_all_brands(persist_to_db=persist_to_db))
        return

    if args.mode == "summary":
        run_executive_summary()
        return

    if args.mode == "specs":
        run_product_spec_extraction(limit=args.limit, include_existing=args.refresh_specs)
        return

    if args.mode == "report":
        run_weekly_report_generation(send_email=args.email_report)
        return

    if args.brand:
        run_catalog_diff(args.brand)
    else:
        run_catalog_diff_for_all_brands()


if __name__ == "__main__":
    main()
