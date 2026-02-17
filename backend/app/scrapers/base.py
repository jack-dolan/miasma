"""
Base scraper class with common functionality for all data broker scrapers
"""

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class ScraperResult:
    """Standardized result format for all scrapers"""
    
    def __init__(
        self,
        source: str,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        self.source = source
        self.success = success
        self.data = data or {}
        self.error = error
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }


class BaseScraper(ABC):
    """
    Base class for all data broker scrapers
    Provides common functionality: driver setup, delays, error handling
    """
    
    def __init__(self):
        self.driver: Optional[webdriver.Remote] = None
        self.source_name = self.__class__.__name__.replace("Scraper", "")
        
    async def initialize_driver(self) -> bool:
        """Initialize Selenium WebDriver with Chrome options"""
        try:
            chrome_options = webdriver.ChromeOptions()
            
            # Parse chrome options from settings
            for option in settings.CHROME_OPTIONS.split(','):
                chrome_options.add_argument(option.strip())
            
            # Set user agent
            chrome_options.add_argument(f'user-agent={settings.USER_AGENT}')
            
            # Additional options for stability
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Connect to Selenium Hub
            self.driver = webdriver.Remote(
                command_executor=settings.SELENIUM_HUB_URL,
                options=chrome_options
            )
            
            # Set timeouts
            self.driver.set_page_load_timeout(settings.PAGE_LOAD_TIMEOUT)
            self.driver.implicitly_wait(settings.SELENIUM_TIMEOUT)
            
            logger.info(f"{self.source_name}: WebDriver initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"{self.source_name}: Failed to initialize WebDriver: {e}")
            return False
    
    async def close_driver(self):
        """Safely close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info(f"{self.source_name}: WebDriver closed")
            except Exception as e:
                logger.error(f"{self.source_name}: Error closing WebDriver: {e}")
            finally:
                self.driver = None
    
    async def random_delay(self, min_seconds: Optional[float] = None, max_seconds: Optional[float] = None):
        """Add random delay to mimic human behavior"""
        min_delay = min_seconds or settings.REQUEST_DELAY_MIN
        max_delay = max_seconds or settings.REQUEST_DELAY_MAX
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    async def safe_get(self, url: str, retries: int = 3) -> bool:
        """Safely navigate to URL with retries"""
        for attempt in range(retries):
            try:
                self.driver.get(url)
                await self.random_delay()
                return True
            except TimeoutException:
                logger.warning(f"{self.source_name}: Timeout loading {url}, attempt {attempt + 1}/{retries}")
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
        Perform search on the data broker site
        Must be implemented by each scraper
        """
        pass
    
    @abstractmethod
    def parse_results(self) -> Dict[str, Any]:
        """
        Parse search results from the page
        Must be implemented by each scraper
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
        """
        Main scraping workflow with error handling
        """
        try:
            # Initialize driver
            if not await self.initialize_driver():
                return ScraperResult(
                    source=self.source_name,
                    success=False,
                    error="Failed to initialize WebDriver"
                )
            
            # Perform search
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