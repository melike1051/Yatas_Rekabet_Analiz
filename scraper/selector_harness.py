from __future__ import annotations

import asyncio
from argparse import ArgumentParser
import json
from pathlib import Path
from typing import Any

from scraper.brands.brand_configs import BRAND_CONFIGS
from scraper.utils.logging_config import get_logger
from scraper.utils.normalizers import dump_json

logger = get_logger("scraper.selector_harness")
SUPPORTED_BRANDS = ("istikbal", "bellona", "dogtas")


def get_scraper_classes() -> dict[str, type]:
    from scraper.brands.bellona import BellonaScraper
    from scraper.brands.dogtas import DogtasScraper
    from scraper.brands.istikbal import IstikbalScraper

    return {
        "istikbal": IstikbalScraper,
        "bellona": BellonaScraper,
        "dogtas": DogtasScraper,
    }


async def validate_brand_selectors(
    brand: str,
    url_override: str | None = None,
    wait_until: str = "domcontentloaded",
) -> dict[str, Any]:
    scraper_cls = get_scraper_classes()[brand]
    config = BRAND_CONFIGS[brand]
    target_url = url_override or config.get("category_sources", [{"url": config["openable_table_url"]}])[0]["url"]

    async with scraper_cls() as scraper:
        page = await scraper.fetch_page(target_url, wait_until=wait_until)
        try:
            product_card_count = await page.locator(config["selectors"]["product_card"]).count()
            sample_text = await scraper.safe_inner_text(page, config["selectors"]["product_name"])
            screenshot = await scraper.capture_screenshot(page, f"{brand}_selector_check")
            html_dump = await scraper.capture_html(page, f"{brand}_selector_check")
            page_title = await page.title()
            final_url = page.url
            json_ld_product_count = await _count_json_ld_products(page)
        finally:
            await page.close()

    result = {
        "brand": brand,
        "base_url": config["base_url"],
        "openable_table_url": target_url,
        "final_url": final_url,
        "page_title": page_title,
        "selectors": config["selectors"],
        "product_card_count": product_card_count,
        "json_ld_product_count": json_ld_product_count,
        "sample_product_name": sample_text,
        "screenshot": str(screenshot),
        "html_dump": str(html_dump),
        "selector_status": "ok" if product_card_count > 0 or json_ld_product_count > 0 else "needs_review",
    }
    logger.info("Selector validation completed", extra={"extra_fields": result})
    return result


async def validate_all_brands() -> list[dict[str, Any]]:
    results = []
    for brand in get_scraper_classes():
        results.append(await validate_brand_selectors(brand))
    return results


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Validate scraper selectors against live pages")
    parser.add_argument("--brand", choices=sorted(SUPPORTED_BRANDS))
    parser.add_argument("--url")
    parser.add_argument(
        "--wait-until",
        choices=["commit", "domcontentloaded", "load", "networkidle"],
        default="domcontentloaded",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.brand:
        results = [asyncio.run(validate_brand_selectors(args.brand, args.url, args.wait_until))]
    else:
        results = asyncio.run(validate_all_brands())

    output_path = Path("scraper/data/selector_validation.json")
    dump_json(output_path, results)
    print(output_path)


async def _count_json_ld_products(page: Any) -> int:
    script_locator = page.locator("script[type='application/ld+json']")
    script_count = await script_locator.count()
    total = 0
    for index in range(script_count):
        raw_text = await script_locator.nth(index).inner_text()
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            continue

        entities = []
        if isinstance(payload, dict) and isinstance(payload.get("mainEntity"), list):
            entities = payload["mainEntity"]
        elif isinstance(payload, list):
            entities = payload

        total += sum(1 for entity in entities if isinstance(entity, dict) and entity.get("@type") == "Product")
    return total


if __name__ == "__main__":
    main()
