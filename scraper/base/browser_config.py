from __future__ import annotations

from dataclasses import dataclass, field
from random import choice
from typing import Optional


DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
]


@dataclass
class BrowserProfile:
    headless: bool = True
    viewport_width: int = 1440
    viewport_height: int = 900
    navigation_timeout_ms: int = 45000
    selector_timeout_ms: int = 15000
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0
    user_agents: list[str] = field(default_factory=lambda: DEFAULT_USER_AGENTS.copy())
    proxies: list[str] = field(default_factory=list)
    locale: str = "tr-TR"
    timezone_id: str = "Europe/Istanbul"
    launch_args: list[str] = field(
        default_factory=lambda: [
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-gpu",
        ]
    )

    def random_user_agent(self) -> str:
        return choice(self.user_agents)

    def next_proxy(self) -> Optional[dict[str, str]]:
        if not self.proxies:
            return None
        return {"server": choice(self.proxies)}
