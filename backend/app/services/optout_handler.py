"""
Base classes for opt-out automation handlers.

Opt-out handlers use Camoufox (Playwright antidetect Firefox) to automate
data-broker removal flows in a consistent way.
"""

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


@dataclass
class OptoutResult:
    """Standard result payload from an opt-out handler."""

    site: str
    success: bool
    removed: bool = False
    reference_id: Optional[str] = None
    error: Optional[str] = None
    attempted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)


class BaseOptoutHandler(ABC):
    """
    Base class for site-specific opt-out handlers.

    Subclasses should implement `perform_optout()` with site-specific steps.
    """

    PAGE_LOAD_TIMEOUT_MS = 30000
    TURNSTILE_TIMEOUT_SEC = 20
    REQUEST_DELAY_MIN = 2.0
    REQUEST_DELAY_MAX = 5.0

    def __init__(self, site_name: str):
        self.site_name = site_name
        self._context_manager = None
        self._browser = None
        self._page = None

    async def open(self) -> None:
        """Open Camoufox browser session and create a page."""
        if self._browser:
            return

        try:
            from camoufox.async_api import AsyncCamoufox
        except ImportError as exc:
            raise RuntimeError(
                "camoufox is required for opt-out handlers. Install camoufox and dependencies."
            ) from exc

        self._context_manager = AsyncCamoufox(
            headless="virtual",
            humanize=True,
        )
        self._browser = await self._context_manager.__aenter__()
        self._page = await self._browser.new_page()
        logger.info("%s: browser session opened", self.site_name)

    async def close(self) -> None:
        """Close Camoufox browser session."""
        if not self._context_manager:
            return

        try:
            await self._context_manager.__aexit__(None, None, None)
        finally:
            self._context_manager = None
            self._browser = None
            self._page = None
            logger.info("%s: browser session closed", self.site_name)

    async def execute(self, profile: Dict[str, Any]) -> OptoutResult:
        """Run full opt-out flow with lifecycle and error handling."""
        try:
            await self.open()
            return await self.perform_optout(profile)
        except Exception as exc:
            logger.error("%s: opt-out failed: %s", self.site_name, exc, exc_info=True)
            return OptoutResult(
                site=self.site_name,
                success=False,
                removed=False,
                error=str(exc),
            )
        finally:
            await self.close()

    async def _goto(self, url: str) -> None:
        """Navigate to URL and wait for network idle."""
        await self._require_page()
        await self._page.goto(url, timeout=self.PAGE_LOAD_TIMEOUT_MS, wait_until="networkidle")
        await self._random_delay()

    async def _random_delay(self, min_seconds: Optional[float] = None, max_seconds: Optional[float] = None) -> None:
        """Small human-like pause between actions."""
        min_delay = min_seconds if min_seconds is not None else self.REQUEST_DELAY_MIN
        max_delay = max_seconds if max_seconds is not None else self.REQUEST_DELAY_MAX
        delay = min_delay if max_delay <= min_delay else random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)

    async def _solve_turnstile_if_present(self) -> bool:
        """
        Attempt to solve Cloudflare Turnstile challenge if present.

        Returns True when page is usable (challenge solved or absent).
        """
        await self._require_page()
        title = (await self._page.title()).lower()
        if "just a moment" not in title and "security challenge" not in title:
            return True

        logger.info("%s: Turnstile detected; attempting solve", self.site_name)
        await self._page.wait_for_timeout(3000)

        clicked = False
        for frame in self._page.frames:
            if "challenges.cloudflare.com" in frame.url:
                try:
                    await frame.click("body")
                    clicked = True
                    break
                except Exception as exc:
                    logger.warning("%s: failed to click Turnstile frame: %s", self.site_name, exc)

        if not clicked:
            logger.warning("%s: Turnstile iframe not found", self.site_name)

        checks = self.TURNSTILE_TIMEOUT_SEC // 2
        for _ in range(checks):
            await self._page.wait_for_timeout(2000)
            title = (await self._page.title()).lower()
            if "just a moment" not in title and "security challenge" not in title:
                return True

        return False

    async def _require_page(self) -> None:
        if self._page is None:
            raise RuntimeError("Browser page is not initialized")

    @abstractmethod
    async def perform_optout(self, profile: Dict[str, Any]) -> OptoutResult:
        """Execute site-specific opt-out steps."""
        raise NotImplementedError
