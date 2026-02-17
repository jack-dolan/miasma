"""
Radaris.com scraper implementation
"""

import logging
import re
from typing import Dict, List, Optional, Any

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

from app.scrapers.base import BaseScraper, ScraperResult

logger = logging.getLogger(__name__)


class RadarisScraper(BaseScraper):
    """Scraper for Radaris.com"""

    BASE_URL = "https://radaris.com"

    def _build_search_url(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None
    ) -> str:
        """Build the search URL based on available parameters"""
        # Radaris uses path format: /p/Firstname/Lastname/ or with location
        first = first_name.capitalize()
        last = last_name.capitalize()

        if city and state:
            city_formatted = city.replace(" ", "-")
            return f"{self.BASE_URL}/p/{first}/{last}/{city_formatted}-{state.upper()}/"
        elif state:
            return f"{self.BASE_URL}/ng/search?ff={first}&fl={last}&fs={state}"
        else:
            return f"{self.BASE_URL}/p/{first}/{last}/"

    async def search(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        age: Optional[int] = None
    ) -> ScraperResult:
        """Perform search on Radaris"""

        try:
            search_url = self._build_search_url(first_name, last_name, city, state)
            logger.info(f"Radaris: Searching at {search_url}")

            # Navigate to search page
            if not await self.safe_get(search_url):
                return ScraperResult(
                    source=self.source_name,
                    success=False,
                    error="Failed to load search page"
                )

            # Wait for page to load
            await self.random_delay(2, 4)

            # Check for blocks
            page_title = self.driver.title.lower()
            page_source = self.driver.page_source.lower()

            if "just a moment" in page_title or "cloudflare" in page_source:
                logger.warning("Radaris: Cloudflare protection detected, waiting...")
                await self.random_delay(5, 10)

            if "blocked" in page_title or "access denied" in page_source:
                logger.error("Radaris: Access blocked")
                return ScraperResult(
                    source=self.source_name,
                    success=False,
                    error="Access blocked by site"
                )

            # Parse results
            data = self.parse_results()

            if not data or not data.get("results"):
                try:
                    self.driver.save_screenshot("radaris_debug.png")
                    with open("radaris_page.html", "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                    logger.info("DEBUG: Saved Radaris screenshot and HTML")
                except Exception as e:
                    logger.warning(f"Could not save debug files: {e}")

                return ScraperResult(
                    source=self.source_name,
                    success=True,
                    data={"message": "No results found", "results": []}
                )

            return ScraperResult(
                source=self.source_name,
                success=True,
                data=data
            )

        except Exception as e:
            logger.error(f"Radaris search failed: {e}", exc_info=True)
            return ScraperResult(
                source=self.source_name,
                success=False,
                error=str(e)
            )

    def parse_results(self) -> Dict[str, Any]:
        """Parse search results from Radaris using BeautifulSoup for faster parsing"""

        results = []

        try:
            # Get page source and parse with BeautifulSoup (much faster than Selenium calls)
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Try multiple selectors for result cards
            result_selectors = [
                "div.card-summary",
                "div[class*='teaser']",
                "div[class*='person']",
                "div[class*='result']",
                "article",
                "div.card"
            ]

            result_cards = []
            for selector in result_selectors:
                cards = soup.select(selector)
                if cards:
                    result_cards = cards
                    logger.info(f"Found {len(cards)} results with selector: {selector}")
                    break

            for card in result_cards[:10]:
                try:
                    result_data = self._parse_result_card_bs(card)
                    if result_data and result_data.get("name"):
                        results.append(result_data)
                except Exception as e:
                    logger.warning(f"Error parsing Radaris result card: {e}")
                    continue

            logger.info(f"Successfully parsed {len(results)} person records")
            return {
                "results": results,
                "total_found": len(results)
            }

        except Exception as e:
            logger.error(f"Error parsing Radaris results: {e}", exc_info=True)
            return {"results": [], "total_found": 0}

    def _parse_result_card_bs(self, card) -> Optional[Dict[str, Any]]:
        """Parse individual result card using BeautifulSoup"""

        result = {
            "name": None,
            "age": None,
            "location": None,
            "addresses": [],
            "phone_numbers": [],
            "profile_url": None
        }

        try:
            card_text = card.get_text(separator=' ', strip=True)

            # Find name - try various selectors
            name_selectors = ["h2 a", "h3 a", ".name", "a[itemprop='url']", ".card-title", "strong a", "a[href*='/p/']"]
            for sel in name_selectors:
                elem = card.select_one(sel)
                if elem and elem.get_text(strip=True):
                    result["name"] = elem.get_text(strip=True)
                    href = elem.get('href')
                    if href:
                        if not href.startswith('http'):
                            href = f"https://radaris.com{href}"
                        result["profile_url"] = href
                    break

            # Find age
            age_match = re.search(r'(?:age|Age)[:\s]*(\d+)', card_text)
            if age_match:
                result["age"] = int(age_match.group(1))
            else:
                # Try pattern like "47 years old"
                age_match = re.search(r'(\d+)\s*years?\s*old', card_text, re.IGNORECASE)
                if age_match:
                    result["age"] = int(age_match.group(1))

            # Find location - extract city, state pattern from text
            location_match = re.search(r'([A-Za-z\s]+),\s*([A-Z]{2})\b', card_text)
            if location_match:
                city = location_match.group(1).strip()
                # Clean up common prefixes
                city = re.sub(r'^(View\s+Profile\s*)', '', city, flags=re.IGNORECASE).strip()
                if city:
                    result["location"] = f"{city}, {location_match.group(2)}"
                    result["addresses"].append(result["location"])

            # Also try to extract age from name if format is "Name, Age"
            if not result["age"] and result["name"]:
                name_age_match = re.match(r'^(.+?),\s*(\d+)$', result["name"])
                if name_age_match:
                    result["name"] = name_age_match.group(1).strip()
                    result["age"] = int(name_age_match.group(2))

            # Find phone
            phone_matches = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', card_text)
            for phone in phone_matches:
                if phone not in result["phone_numbers"]:
                    result["phone_numbers"].append(phone)

            return result if result["name"] else None

        except Exception as e:
            logger.warning(f"Error parsing Radaris result card details: {e}")
            return None
