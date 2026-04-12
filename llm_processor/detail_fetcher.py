from __future__ import annotations

import asyncio
from typing import Optional

from scraper.base.base_scraper import BaseScraper


DETAIL_TEXT_SELECTORS = [
    ".product-detail__description",
    ".product-description",
    ".description",
    ".tab-content",
    ".product-content",
    ".product-detail",
    ".urun-detay",
]

TECHNICAL_TEXT_SELECTORS = [
    ".technical-specifications",
    ".product-specifications",
    ".specifications",
    ".tech-specs",
    ".urun-ozellikleri",
]


class ProductDetailFetcher(BaseScraper):
    def __init__(self) -> None:
        super().__init__(competitor_name="product_detail_fetcher")

    async def scrape_daily(self) -> list[dict]:
        return []

    async def scrape_catalog(self) -> list[dict]:
        return []

    async def fetch_detail_context(self, product_url: str) -> dict:
        page = await self.fetch_page(product_url)
        try:
            title = await page.title()
            meta_description = await self.safe_attribute(page, "meta[name='description']", "content")
            description_text = await self._collect_text(page, DETAIL_TEXT_SELECTORS)
            technical_text = await self._collect_text(page, TECHNICAL_TEXT_SELECTORS)
            body_excerpt = await page.locator("body").inner_text()
            return {
                "title": title,
                "meta_description": meta_description,
                "description_text": description_text,
                "technical_text": technical_text,
                "body_excerpt": body_excerpt[:4000] if body_excerpt else None,
            }
        finally:
            await page.close()

    async def _collect_text(self, page, selectors: list[str]) -> Optional[str]:
        for selector in selectors:
            locator = page.locator(selector)
            count = await locator.count()
            if count == 0:
                continue
            text = await locator.first.inner_text()
            if text and text.strip():
                return text.strip()
        return None
