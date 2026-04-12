from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from pathlib import Path
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from scraper.base.browser_config import BrowserProfile
from scraper.utils.logging_config import get_logger


class BaseScraper(ABC):
    def __init__(self, competitor_name: str, browser_profile: BrowserProfile | None = None):
        self.competitor_name = competitor_name
        self.browser_profile = browser_profile or BrowserProfile()
        self.logger = get_logger(f"scraper.{competitor_name}")
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def __aenter__(self) -> "BaseScraper":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def start(self) -> None:
        self.logger.info(
            "Browser startup initiated",
            extra={"extra_fields": {"competitor": self.competitor_name}},
        )
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.browser_profile.headless,
            proxy=self.browser_profile.next_proxy(),
            args=self.browser_profile.launch_args,
        )
        self._context = await self._browser.new_context(
            user_agent=self.browser_profile.random_user_agent(),
            viewport={
                "width": self.browser_profile.viewport_width,
                "height": self.browser_profile.viewport_height,
            },
            locale=self.browser_profile.locale,
            timezone_id=self.browser_profile.timezone_id,
        )
        self._context.set_default_navigation_timeout(self.browser_profile.navigation_timeout_ms)
        self._context.set_default_timeout(self.browser_profile.selector_timeout_ms)

    async def close(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def new_page(self) -> Page:
        if not self._context:
            raise RuntimeError("Browser context is not initialized. Call start() first.")
        return await self._context.new_page()

    async def fetch_page(self, url: str, wait_until: str = "domcontentloaded") -> Page:
        last_error: Exception | None = None
        for attempt in range(1, self.browser_profile.max_retries + 1):
            page = await self.new_page()
            try:
                self.logger.info(
                    "Navigating to page",
                    extra={
                        "extra_fields": {
                            "competitor": self.competitor_name,
                            "url": url,
                            "attempt": attempt,
                        }
                    },
                )
                await page.goto(url, wait_until=wait_until)
                return page
            except Exception as exc:
                last_error = exc
                screenshot = await self.capture_screenshot(
                    page,
                    f"{self.competitor_name.lower()}_navigation_error_attempt_{attempt}",
                )
                html_dump = await self.capture_html(
                    page,
                    f"{self.competitor_name.lower()}_navigation_error_attempt_{attempt}",
                )
                self.logger.warning(
                    "Navigation failed",
                    extra={
                        "extra_fields": {
                            "competitor": self.competitor_name,
                            "url": url,
                            "attempt": attempt,
                            "screenshot": str(screenshot) if screenshot else None,
                            "html_dump": str(html_dump) if html_dump else None,
                        }
                    },
                    exc_info=exc,
                )
                await page.close()
                if attempt < self.browser_profile.max_retries:
                    await asyncio.sleep(self.browser_profile.retry_backoff_seconds * attempt)

        assert last_error is not None
        raise last_error

    async def capture_screenshot(self, page: Page, name: str) -> Path | None:
        output_dir = Path("scraper/data/screenshots")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{name}.png"
        try:
            await page.screenshot(path=str(output_path), full_page=True)
            return output_path
        except Exception as exc:
            self.logger.warning(
                "Screenshot capture failed",
                extra={
                    "extra_fields": {
                        "competitor": self.competitor_name,
                        "artifact_path": str(output_path),
                    }
                },
                exc_info=exc,
            )
            return None

    async def capture_html(self, page: Page, name: str) -> Path | None:
        output_dir = Path("scraper/data/html")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{name}.html"
        try:
            output_path.write_text(await page.content(), encoding="utf-8")
            return output_path
        except Exception as exc:
            self.logger.warning(
                "HTML capture failed",
                extra={
                    "extra_fields": {
                        "competitor": self.competitor_name,
                        "artifact_path": str(output_path),
                    }
                },
                exc_info=exc,
            )
            return None

    async def safe_inner_text(self, page_or_locator: Any, selector: str) -> str | None:
        locator = page_or_locator.locator(selector)
        count = await locator.count()
        if count == 0:
            return None
        text = await locator.first.inner_text()
        return text.strip() if text else None

    async def safe_attribute(self, page_or_locator: Any, selector: str, attribute: str) -> str | None:
        locator = page_or_locator.locator(selector)
        count = await locator.count()
        if count == 0:
            return None
        value = await locator.first.get_attribute(attribute)
        return value.strip() if isinstance(value, str) else value

    @abstractmethod
    async def scrape_daily(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def scrape_catalog(self) -> list[dict[str, Any]]:
        raise NotImplementedError
