from __future__ import annotations

import json
from typing import Any

from scraper.base.base_scraper import BaseScraper
from scraper.schemas import ScrapedProduct, ScrapedPromotion
from scraper.utils.campaigns import classify_campaign_message, is_campaign_line, normalize_campaign_text
from scraper.utils.dining_room import classify_product, clean_product_name
from scraper.utils.normalizers import infer_stock_state, parse_discount_rate, parse_price


class FurnitureBrandScraper(BaseScraper):
    def __init__(self, competitor_name: str, config: dict[str, Any]):
        super().__init__(competitor_name=competitor_name)
        self.config = config
        self.selectors = config["selectors"]

    async def scrape_daily(self) -> list[dict[str, Any]]:
        product_index: dict[str, dict[str, Any]] = {}
        for source in self._listing_sources():
            page = await self.fetch_page(source["url"])
            try:
                items = await page.locator(self.selectors["product_card"]).all()
                extracted_products = [
                    await self._extract_product_payload(item, source["category_name"])
                    for item in items
                ]
                products = [product for product in extracted_products if product is not None]
                if not products:
                    products = await self._extract_products_from_json_ld(page, source["category_name"])
                for product in products:
                    self._merge_product_record(product_index, product)
            except Exception as exc:
                html_path = await self.capture_html(page, f"{self.competitor_name.lower()}_daily_failure")
                self.logger.error(
                    "Daily scrape failed",
                    extra={
                        "extra_fields": {
                            "competitor": self.competitor_name,
                            "html_dump": str(html_path),
                            "source_url": source["url"],
                        }
                    },
                    exc_info=exc,
                )
                raise
            finally:
                await page.close()

        products = list(product_index.values())
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

    async def scrape_catalog(self) -> list[dict[str, Any]]:
        catalog_index: dict[str, dict[str, Any]] = {}
        for source in self._listing_sources():
            page = await self.fetch_page(source["url"])
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
                    product_name = clean_product_name(product_name)
                    classification = classify_product(product_name)
                    catalog.append(
                        {
                            "competitor_name": self.competitor_name,
                            "category_name": classification["item_type"],
                            "competitor_sku": sku_attr or href or product_name,
                            "product_name": product_name,
                            "product_url": self._absolute_url(href),
                            "raw_attributes": classification,
                        }
                    )

                if not catalog:
                    catalog = await self._extract_products_from_json_ld(page, source["category_name"])
                    catalog = [
                        {
                            "competitor_name": product["competitor_name"],
                            "category_name": product["category_name"],
                            "competitor_sku": product["competitor_sku"],
                            "product_name": product["product_name"],
                            "product_url": product["product_url"],
                            "raw_attributes": product.get("raw_attributes", {}),
                        }
                        for product in catalog
                    ]

                for item in catalog:
                    self._merge_product_record(catalog_index, item)
            except Exception as exc:
                html_path = await self.capture_html(page, f"{self.competitor_name.lower()}_catalog_failure")
                self.logger.error(
                    "Catalog scrape failed",
                    extra={
                        "extra_fields": {
                            "competitor": self.competitor_name,
                            "html_dump": str(html_path),
                            "source_url": source["url"],
                        }
                    },
                    exc_info=exc,
                )
                raise
            finally:
                await page.close()

        catalog = list(catalog_index.values())
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

    async def scrape_promotions(self) -> list[dict[str, Any]]:
        page = await self.fetch_page(self.config["campaigns_url"])
        try:
            promotions = await self._extract_promotion_payloads(page)
            if not promotions:
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
            return self._listing_sources()[0]["url"]
        if href.startswith("//"):
            return f"https:{href}"
        if href.startswith("http"):
            return href
        return f"{self.config['base_url'].rstrip('/')}/{href.lstrip('/')}"

    def _listing_sources(self) -> list[dict[str, str]]:
        sources = self.config.get("category_sources")
        if sources:
            return sources
        return [{"category_name": "Yemek Odasi", "url": self.config["openable_table_url"]}]

    async def _extract_product_payload(self, item: Any, source_category_name: str) -> dict[str, Any] | None:
        price_text = await self.safe_inner_text(item, self.selectors["product_price"])
        original_price_text = await self.safe_inner_text(item, self.selectors["original_price"])
        href = await self.safe_attribute(item, self.selectors["product_link"], "href")
        image_url = await self._extract_image_url(item)
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
        if not product_name:
            self.logger.warning(
                "Skipped product card without name",
                extra={"extra_fields": {"competitor": self.competitor_name}},
            )
            return None

        product_name = clean_product_name(product_name)
        classification = classify_product(product_name)
        price = parse_price(price_text)
        original_price = parse_price(original_price_text)
        return ScrapedProduct(
            competitor_name=self.competitor_name,
            competitor_sku=sku_attr or href or product_name,
            product_name=product_name,
            category_name=str(classification["item_type"] or source_category_name),
            product_url=self._absolute_url(href),
            image_url=image_url,
            current_price=price,
            original_price=original_price,
            discount_rate=parse_discount_rate(price, original_price),
            in_stock=infer_stock_state(stock_text),
            promotion_label=promotion_label or None,
            raw_attributes={
                "source_category_name": source_category_name,
                "image_url": image_url,
                **classification,
            },
            raw_payload={
                "href": href,
                "image_url": image_url,
                "stock_text": stock_text,
                "price_text": price_text,
                "original_price_text": original_price_text,
            },
        ).model_dump(mode="json")

    def _merge_product_record(self, product_index: dict[str, dict[str, Any]], product: dict[str, Any]) -> None:
        product_key = str(product.get("competitor_sku") or product.get("product_url") or product.get("product_name"))
        existing = product_index.get(product_key)
        if not existing:
            product_index[product_key] = product
            return

        for field in ("current_price", "original_price", "discount_rate", "promotion_label", "in_stock"):
            if existing.get(field) is None and product.get(field) is not None:
                existing[field] = product[field]
        existing_raw = dict(existing.get("raw_attributes") or {})
        incoming_raw = dict(product.get("raw_attributes") or {})
        existing["raw_attributes"] = {**incoming_raw, **existing_raw}
        existing_payload = dict(existing.get("raw_payload") or {})
        incoming_payload = dict(product.get("raw_payload") or {})
        existing["raw_payload"] = {**existing_payload, **incoming_payload}

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

    async def _extract_products_from_json_ld(self, page: Any, source_category_name: str) -> list[dict[str, Any]]:
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
                image_value = entity.get("image")
                if isinstance(image_value, list):
                    image_value = next((item for item in image_value if isinstance(item, str) and item.strip()), None)
                image_url = self._absolute_url(image_value) if isinstance(image_value, str) else None

                if not name:
                    continue

                name = clean_product_name(name)
                classification = classify_product(name)
                products.append(
                    ScrapedProduct(
                        competitor_name=self.competitor_name,
                        competitor_sku=slug,
                        product_name=name,
                        category_name=str(classification["item_type"] or source_category_name),
                        product_url=self._absolute_url(relative_url),
                        image_url=image_url,
                        current_price=price,
                        in_stock=in_stock,
                        raw_attributes={
                            "source_category_name": source_category_name,
                            "image_url": image_url,
                            **classification,
                        },
                        raw_payload={"source": "json_ld", "offers": offers, "image_url": image_url},
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

    async def _extract_image_url(self, item: Any) -> str | None:
        selectors = [
            ".image-wrapper .image img",
            ".carousel-inner img",
            "picture img",
            ".image img",
            "img",
        ]
        for selector in selectors:
            image_locator = item.locator(selector)
            count = await image_locator.count()
            for index in range(count):
                image = image_locator.nth(index)
                candidate = await self._extract_image_candidate(image)
                if candidate:
                    return candidate
        return None

    async def _extract_image_candidate(self, image: Any) -> str | None:
        for attribute in ("src", "data-src", "data-original", "data-lazy-src", "data-srcset"):
            value = await image.get_attribute(attribute)
            candidate = self._normalize_image_candidate(value)
            if candidate:
                return candidate
        srcset = await image.get_attribute("srcset")
        if isinstance(srcset, str) and srcset.strip():
            for source in srcset.split(","):
                first_candidate = source.strip().split(" ")[0].strip()
                candidate = self._normalize_image_candidate(first_candidate)
                if candidate:
                    return candidate
        return None

    def _normalize_image_candidate(self, value: str | None) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None
        candidate = self._absolute_url(value.strip())
        lowered = candidate.casefold()
        invalid_markers = (
            "icon",
            "logo",
            "cart-heart",
            "header-heart",
            "header-cart",
            "header-user",
            "gift-box",
            "search-icon",
            "magnifying-glass",
            "list.svg",
            ".svg",
        )
        if any(marker in lowered for marker in invalid_markers):
            return None
        return candidate

    async def _extract_promotion_payloads(self, page: Any) -> list[dict[str, Any]]:
        candidates = await self._collect_campaign_candidates(page)
        promotions: list[dict[str, Any]] = []
        for message in candidates[:20]:
            classification = classify_campaign_message(message)
            promotions.append(
                ScrapedPromotion(
                    competitor_name=self.competitor_name,
                    title=message[:120],
                    description=message,
                    promotion_type=classification["promotion_type"],
                    raw_payload={
                        "source_url": self.config["campaigns_url"],
                        "normalized_message": classification["normalized_message"],
                        "discount_value": str(classification["discount_value"]) if classification["discount_value"] is not None else None,
                        "discount_unit": classification["discount_unit"],
                        "installment_months": classification["installment_months"],
                        "campaign_scope": classification["campaign_scope"],
                    },
                ).model_dump(mode="json")
            )
        return promotions

    async def _collect_campaign_candidates(self, page: Any) -> list[str]:
        selectors = [
            "body",
            "main a",
            "main button",
            "main [title]",
            "main img[alt]",
            "section a",
            "section h1, section h2, section h3, section h4, section p, section span",
        ]
        candidates: list[str] = []
        seen_messages: set[str] = set()

        async def add_candidate(raw_value: str | None) -> None:
            normalized_value = normalize_campaign_text(raw_value)
            if not is_campaign_line(normalized_value):
                return
            lowered = normalized_value.casefold()
            if lowered in seen_messages:
                return
            seen_messages.add(lowered)
            candidates.append(normalized_value)

        for selector in selectors:
            locator = page.locator(selector)
            try:
                count = await locator.count()
            except Exception:
                continue
            if count == 0:
                continue
            if selector == "body":
                try:
                    body_text = await locator.first.inner_text()
                except Exception:
                    continue
                for line in body_text.splitlines():
                    await add_candidate(line)
                continue

            limited_count = min(count, 60)
            for index in range(limited_count):
                node = locator.nth(index)
                for accessor in ("inner_text",):
                    try:
                        value = await getattr(node, accessor)()
                    except Exception:
                        value = None
                    await add_candidate(value)
                for attribute_name in ("title", "aria-label", "alt"):
                    try:
                        attr_value = await node.get_attribute(attribute_name)
                    except Exception:
                        attr_value = None
                    await add_candidate(attr_value)
        return candidates
