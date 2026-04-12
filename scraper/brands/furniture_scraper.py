from __future__ import annotations

import json
from typing import Any

from scraper.base.base_scraper import BaseScraper
from scraper.schemas import ScrapedProduct, ScrapedPromotion
from scraper.utils.normalizers import infer_stock_state, parse_discount_rate, parse_price


class FurnitureBrandScraper(BaseScraper):
    def __init__(self, competitor_name: str, config: dict[str, Any]):
        super().__init__(competitor_name=competitor_name)
        self.config = config
        self.selectors = config["selectors"]

    async def scrape_daily(self) -> list[dict[str, Any]]:
        page = await self.fetch_page(self.config["openable_table_url"])
        try:
            items = await page.locator(self.selectors["product_card"]).all()
            products: list[dict[str, Any]] = []

            for item in items:
                price_text = await self.safe_inner_text(item, self.selectors["product_price"])
                original_price_text = await self.safe_inner_text(item, self.selectors["original_price"])
                href = await self.safe_attribute(item, self.selectors["product_link"], "href")
                sku_attr = await self._extract_sku(item)
                stock_text = await self.safe_inner_text(item, self.selectors["stock_label"])
                promotion_label = await self.safe_inner_text(item, self.selectors["promotion_badge"])
                product_name = await self.safe_inner_text(item, self.selectors["product_name"])
                ga4_data = await self._extract_ga4_data(item)
                if not product_name:
                    product_name = await self.safe_attribute(item, self.selectors["product_link"], "title")
                if ga4_data:
                    product_name = product_name or ga4_data.get("name")
                    sku_attr = sku_attr or ga4_data.get("sku") or ga4_data.get("slug")
                    if not price_text and ga4_data.get("price") is not None:
                        price_text = str(ga4_data["price"])
                price = parse_price(price_text)
                original_price = parse_price(original_price_text)

                if not product_name:
                    self.logger.warning(
                        "Skipped product card without name",
                        extra={"extra_fields": {"competitor": self.competitor_name}},
                    )
                    continue

                payload = ScrapedProduct(
                    competitor_name=self.competitor_name,
                    competitor_sku=sku_attr or href or product_name,
                    product_name=product_name,
                    category_name="Acilir Masa",
                    product_url=self._absolute_url(href),
                    current_price=price,
                    original_price=original_price,
                    discount_rate=parse_discount_rate(price, original_price),
                    in_stock=infer_stock_state(stock_text),
                    promotion_label=promotion_label or None,
                    raw_payload={
                        "href": href,
                        "stock_text": stock_text,
                        "price_text": price_text,
                        "original_price_text": original_price_text,
                    },
                )
                products.append(payload.model_dump(mode="json"))

            if not products:
                products = await self._extract_products_from_json_ld(page)

            self.logger.info(
                "Daily scrape completed",
                extra={
                    "extra_fields": {
                        "competitor": self.competitor_name,
                        "product_count": len(products),
                    }
                },
            )
            return products
        except Exception as exc:
            html_path = await self.capture_html(page, f"{self.competitor_name.lower()}_daily_failure")
            self.logger.error(
                "Daily scrape failed",
                extra={
                    "extra_fields": {
                        "competitor": self.competitor_name,
                        "html_dump": str(html_path),
                    }
                },
                exc_info=exc,
            )
            raise
        finally:
            await page.close()

    async def scrape_catalog(self) -> list[dict[str, Any]]:
        page = await self.fetch_page(self.config["openable_table_url"])
        try:
            items = await page.locator(self.selectors["product_card"]).all()
            catalog: list[dict[str, Any]] = []

            for item in items:
                href = await self.safe_attribute(item, self.selectors["product_link"], "href")
                sku_attr = await self._extract_sku(item)
                product_name = await self.safe_inner_text(item, self.selectors["product_name"])
                ga4_data = await self._extract_ga4_data(item)
                if not product_name:
                    product_name = await self.safe_attribute(item, self.selectors["product_link"], "title")
                if ga4_data:
                    product_name = product_name or ga4_data.get("name")
                    sku_attr = sku_attr or ga4_data.get("sku") or ga4_data.get("slug")
                if not product_name:
                    continue
                catalog.append(
                    {
                        "competitor_name": self.competitor_name,
                        "category_name": "Acilir Masa",
                        "competitor_sku": sku_attr or href or product_name,
                        "product_name": product_name,
                        "product_url": self._absolute_url(href),
                    }
                )

            if not catalog:
                json_ld_products = await self._extract_products_from_json_ld(page)
                catalog = [
                    {
                        "competitor_name": product["competitor_name"],
                        "category_name": product["category_name"],
                        "competitor_sku": product["competitor_sku"],
                        "product_name": product["product_name"],
                        "product_url": product["product_url"],
                    }
                    for product in json_ld_products
                ]

            self.logger.info(
                "Catalog scrape completed",
                extra={
                    "extra_fields": {
                        "competitor": self.competitor_name,
                        "catalog_count": len(catalog),
                    }
                },
            )
            return catalog
        except Exception as exc:
            html_path = await self.capture_html(page, f"{self.competitor_name.lower()}_catalog_failure")
            self.logger.error(
                "Catalog scrape failed",
                extra={
                    "extra_fields": {
                        "competitor": self.competitor_name,
                        "html_dump": str(html_path),
                    }
                },
                exc_info=exc,
            )
            raise
        finally:
            await page.close()

    async def scrape_promotions(self) -> list[dict[str, Any]]:
        page = await self.fetch_page(self.config["campaigns_url"])
        try:
            promotions = [
                ScrapedPromotion(
                    competitor_name=self.competitor_name,
                    title=f"{self.competitor_name.title()} kampanya sayfasi",
                    promotion_type="campaign_page",
                    raw_payload={"source_url": self.config["campaigns_url"]},
                ).model_dump(mode="json")
            ]
            self.logger.info(
                "Promotion scrape completed",
                extra={"extra_fields": {"competitor": self.competitor_name, "promotion_count": len(promotions)}},
            )
            return promotions
        finally:
            await page.close()

    def _absolute_url(self, href: str | None) -> str:
        if not href:
            return self.config["openable_table_url"]
        if href.startswith("http"):
            return href
        return f"{self.config['base_url'].rstrip('/')}/{href.lstrip('/')}"

    async def _extract_sku(self, item: Any) -> str | None:
        selector = self.selectors["sku"]
        locator = item.locator(selector)
        count = await locator.count()
        if count == 0:
            ga4_data = await self._extract_ga4_data(item)
            if ga4_data:
                return ga4_data.get("sku") or ga4_data.get("slug")
            return None

        candidate = await locator.first.get_attribute("data-sku")
        if candidate:
            return candidate.strip()

        candidate = await locator.first.get_attribute("data-product-sku")
        if isinstance(candidate, str):
            return candidate.strip()

        ga4_data = await self._extract_ga4_data(item)
        if ga4_data:
            return ga4_data.get("sku") or ga4_data.get("slug")
        return None

    async def _extract_products_from_json_ld(self, page: Any) -> list[dict[str, Any]]:
        script_locator = page.locator("script[type='application/ld+json']")
        script_count = await script_locator.count()
        products: list[dict[str, Any]] = []

        for index in range(script_count):
            raw_text = await script_locator.nth(index).inner_text()
            try:
                payload = json.loads(raw_text)
            except json.JSONDecodeError:
                continue

            entities = []
            if isinstance(payload, dict):
                main_entity = payload.get("mainEntity")
                if isinstance(main_entity, list):
                    entities = main_entity
            elif isinstance(payload, list):
                entities = payload

            for entity in entities:
                if not isinstance(entity, dict) or entity.get("@type") != "Product":
                    continue

                name = entity.get("name")
                relative_url = entity.get("url")
                offers = entity.get("offers", {}) if isinstance(entity.get("offers"), dict) else {}
                price = parse_price(str(offers.get("price"))) if offers.get("price") is not None else None
                availability = str(offers.get("availability", "")).lower()
                in_stock = True if "instock" in availability else None
                slug = self._derive_slug(relative_url, name)

                if not name:
                    continue

                products.append(
                    ScrapedProduct(
                        competitor_name=self.competitor_name,
                        competitor_sku=slug,
                        product_name=name,
                        category_name="Acilir Masa",
                        product_url=self._absolute_url(relative_url),
                        current_price=price,
                        in_stock=in_stock,
                        raw_payload={"source": "json_ld", "offers": offers},
                    ).model_dump(mode="json")
                )

        return products

    def _derive_slug(self, relative_url: str | None, fallback_name: str | None) -> str:
        if relative_url:
            return relative_url.rstrip("/").split("/")[-1]
        if fallback_name:
            return fallback_name.lower().replace(" ", "-")
        return "unknown-product"

    async def _extract_ga4_data(self, item: Any) -> dict[str, Any] | None:
        raw_data = await item.get_attribute("data-prd-ga4-config")
        if not raw_data:
            return None
        try:
            return json.loads(raw_data)
        except json.JSONDecodeError:
            return None
