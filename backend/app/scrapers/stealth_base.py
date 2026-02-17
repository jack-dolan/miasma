"""
Stealth scraper base class using SeleniumBase UC (Undetected-Chromedriver) Mode.

Alternative to BaseScraper for sites with heavy bot protection (Cloudflare, etc).
UC Mode patches the local chromedriver binary to avoid detection, so it runs Chrome
locally rather than through a remote Selenium Hub.

Requirements:
    pip install seleniumbase
    On Linux without a display, xvfb is needed for the virtual framebuffer:
        sudo apt-get install xvfb
    UC Mode should NOT be run in headless mode (it's detectable). On Linux servers,
    xvfb provides a virtual display so the browser runs "headed" without a real screen.
"""

import asyncio
import logging
import platform
import random
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException
)

from app.core.config import settings
from app.scrapers.base import ScraperResult

logger = logging.getLogger(__name__)

# Check if seleniumbase is available
try:
    from seleniumbase import Driver
    SELENIUMBASE_AVAILABLE = True
except ImportError:
    SELENIUMBASE_AVAILABLE = False
    logger.warning(
        "seleniumbase not installed - StealthScraper will not work. "
        "Install with: pip install seleniumbase"
    )


class StealthScraper(ABC):
    """
    Base class for scrapers that need to bypass heavy bot protection.

    Uses SeleniumBase UC Mode which patches chromedriver to avoid detection.
    The browser runs locally (not through Selenium Hub) with a virtual display
    on Linux to avoid headless detection.

    Provides the same interface as BaseScraper so scrapers can switch between
    them by changing the parent class.
    """

    def __init__(self):
        self.driver = None
        self.source_name = self.__class__.__name__.replace("Scraper", "")

    async def initialize_driver(self) -> bool:
        """Initialize SeleniumBase UC Mode browser"""
        if not SELENIUMBASE_AVAILABLE:
            logger.error(
                f"{self.source_name}: seleniumbase is not installed, "
                "cannot use StealthScraper"
            )
            return False

        try:
            use_xvfb = platform.system() == "Linux"

            # Driver(uc=True) returns a patched webdriver.Chrome instance
            # that's fully compatible with the standard Selenium WebDriver API.
            # xvfb=True uses a virtual display on Linux so we don't need headless
            # (headless is detectable by anti-bot systems).
            self.driver = Driver(
                uc=True,
                xvfb=use_xvfb,
                page_load_strategy="eager",
                block_images=False,
            )

            self.driver.set_page_load_timeout(settings.PAGE_LOAD_TIMEOUT)
            self.driver.implicitly_wait(settings.SELENIUM_TIMEOUT)

            logger.info(f"{self.source_name}: UC Mode browser initialized")
            return True

        except Exception as e:
            logger.error(f"{self.source_name}: Failed to initialize UC Mode browser: {e}")
            return False

    async def close_driver(self):
        """Safely close the browser"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info(f"{self.source_name}: UC Mode browser closed")
            except Exception as e:
                logger.error(f"{self.source_name}: Error closing browser: {e}")
            finally:
                self.driver = None

    async def random_delay(self, min_seconds: Optional[float] = None, max_seconds: Optional[float] = None):
        """Add random delay to mimic human behavior"""
        min_delay = min_seconds or settings.REQUEST_DELAY_MIN
        max_delay = max_seconds or settings.REQUEST_DELAY_MAX
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)

    async def safe_get(self, url: str, retries: int = 3) -> bool:
        """
        Navigate to URL with retries.

        Uses uc_open_with_reconnect which disconnects the browser briefly
        during page load to avoid detection, then reconnects after.
        """
        for attempt in range(retries):
            try:
                # uc_open_with_reconnect is the recommended way to load pages
                # in UC mode - it disconnects chromedriver during the initial
                # page load (when detection scripts run) then reconnects after.
                # The reconnect_time is how many seconds to wait before
                # reconnecting.
                self.driver.uc_open_with_reconnect(url, reconnect_time=4)
                await self.random_delay()
                return True
            except TimeoutException:
                logger.warning(
                    f"{self.source_name}: Timeout loading {url}, "
                    f"attempt {attempt + 1}/{retries}"
                )
                if attempt == retries - 1:
                    return False
            except WebDriverException as e:
                logger.error(f"{self.source_name}: WebDriver error loading {url}: {e}")
                return False
        return False

    def wait_for_element(
        self,
        by: By,
        value: str,
        timeout: int = 10
    ) -> Optional[Any]:
        """Wait for element to be present"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.warning(f"{self.source_name}: Timeout waiting for element: {value}")
            return None

    def find_element_safe(self, by: By, value: str) -> Optional[Any]:
        """Safely find element without throwing exception"""
        try:
            return self.driver.find_element(by, value)
        except NoSuchElementException:
            return None

    def find_elements_safe(self, by: By, value: str) -> List[Any]:
        """Safely find multiple elements"""
        try:
            return self.driver.find_elements(by, value)
        except NoSuchElementException:
            return []

    @abstractmethod
    async def search(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        age: Optional[int] = None
    ) -> ScraperResult:
        """
        Perform search on the data broker site.
        Must be implemented by each scraper.
        """
        pass

    @abstractmethod
    def parse_results(self) -> Dict[str, Any]:
        """
        Parse search results from the page.
        Must be implemented by each scraper.
        """
        pass

    async def scrape(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        age: Optional[int] = None
    ) -> ScraperResult:
        """Main scraping workflow with error handling"""
        try:
            if not await self.initialize_driver():
                return ScraperResult(
                    source=self.source_name,
                    success=False,
                    error="Failed to initialize UC Mode browser"
                )

            result = await self.search(
                first_name=first_name,
                last_name=last_name,
                city=city,
                state=state,
                age=age
            )

            return result

        except Exception as e:
            logger.error(f"{self.source_name}: Scraping failed: {e}", exc_info=True)
            return ScraperResult(
                source=self.source_name,
                success=False,
                error=str(e)
            )

        finally:
            await self.close_driver()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(source={self.source_name})>"
