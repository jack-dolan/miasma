"""
Nuwber.com scraper implementation
"""

import logging
import re
from typing import Dict, List, Optional, Any

from selenium.webdriver.common.by import By

from app.scrapers.base import BaseScraper, ScraperResult

logger = logging.getLogger(__name__)


class NuwberScraper(BaseScraper):
    """Scraper for Nuwber.com"""

    BASE_URL = "https://nuwber.com"

    def _build_search_url(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None
    ) -> str:
        """Build the search URL based on available parameters"""
        # Nuwber uses query params: /search?name=firstname+lastname&city=&state=XX
        name_param = f"{first_name}+{last_name}"
        city_param = city or ""
        state_param = state or ""

        return f"{self.BASE_URL}/search?name={name_param}&city={city_param}&state={state_param}"

    async def search(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        age: Optional[int] = None
    ) -> ScraperResult:
        """Perform search on Nuwber"""

        try:
            search_url = self._build_search_url(first_name, last_name, city, state)
            logger.info(f"Nuwber: Searching at {search_url}")

            # Navigate to search page
            if not await self.safe_get(search_url):
                return ScraperResult(
                    source=self.source_name,
                    success=False,
                    error="Failed to load search page"
                )

            # Wait for page to load
            await self.random_delay(2, 4)

            # Check for Cloudflare or block page
            page_title = self.driver.title.lower()
            page_source = self.driver.page_source.lower()

            if "just a moment" in page_title or "cloudflare" in page_source:
                logger.warning("Nuwber: Cloudflare protection detected, waiting...")
                await self.random_delay(5, 10)

            if "blocked" in page_title or "access denied" in page_source:
                logger.error("Nuwber: Access blocked")
                return ScraperResult(
                    source=self.source_name,
                    success=False,
                    error="Access blocked by site"
                )

            # Parse results
            data = self.parse_results()

            if not data or not data.get("results"):
                # Save debug info
                try:
                    self.driver.save_screenshot("nuwber_debug.png")
                    with open("nuwber_page.html", "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                    logger.info("DEBUG: Saved Nuwber screenshot and HTML")
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
            logger.error(f"Nuwber search failed: {e}", exc_info=True)
            return ScraperResult(
                source=self.source_name,
                success=False,
                error=str(e)
            )

    def parse_results(self) -> Dict[str, Any]:
        """Parse search results from Nuwber"""

        results = []

        try:
            # Nuwber result cards - try multiple selectors
            result_selectors = [
                "div.person-card",
                "div[class*='person']",
                "div[class*='result']",
                "article.person",
                "div.card",
                "a[href*='/person/']"
            ]

            result_cards = []
            for selector in result_selectors:
                cards = self.find_elements_safe(By.CSS_SELECTOR, selector)
                if cards:
                    result_cards = cards
                    logger.info(f"Found {len(cards)} results with selector: {selector}")
                    break

            for card in result_cards[:10]:  # Limit to first 10
                try:
                    result_data = self._parse_result_card(card)
                    if result_data and result_data.get("name"):
                        results.append(result_data)
                except Exception as e:
                    logger.warning(f"Error parsing Nuwber result card: {e}")
                    continue

            return {
                "results": results,
                "total_found": len(results)
            }

        except Exception as e:
            logger.error(f"Error parsing Nuwber results: {e}", exc_info=True)
            return {"results": [], "total_found": 0}

    def _parse_result_card(self, card) -> Optional[Dict[str, Any]]:
        """Parse individual result card"""

        result = {
            "name": None,
            "age": None,
            "location": None,
            "addresses": [],
            "phone_numbers": [],
            "profile_url": None
        }

        try:
            # Try to find name - multiple approaches
            name_selectors = ["h2 a", "h3 a", ".name a", ".person-name", "a[href*='/person/']"]
            for sel in name_selectors:
                try:
                    elem = card.find_element(By.CSS_SELECTOR, sel)
                    if elem and elem.text.strip():
                        result["name"] = elem.text.strip()
                        href = elem.get_attribute("href")
                        if href:
                            result["profile_url"] = href
                        break
                except:
                    continue

            # Try to find age
            age_selectors = [".age", "span[class*='age']", ".person-age"]
            for sel in age_selectors:
                try:
                    elem = card.find_element(By.CSS_SELECTOR, sel)
                    if elem:
                        age_match = re.search(r'\d+', elem.text)
                        if age_match:
                            result["age"] = int(age_match.group())
                        break
                except:
                    continue

            # Try to find location/address
            location_selectors = [".address", ".location", "span[class*='address']", ".person-address"]
            for sel in location_selectors:
                try:
                    elem = card.find_element(By.CSS_SELECTOR, sel)
                    if elem and elem.text.strip():
                        result["location"] = elem.text.strip()
                        result["addresses"].append(elem.text.strip())
                        break
                except:
                    continue

            # Try to find phone
            phone_selectors = [".phone", "a[href^='tel:']", "span[class*='phone']"]
            for sel in phone_selectors:
                try:
                    elems = card.find_elements(By.CSS_SELECTOR, sel)
                    for elem in elems:
                        phone_text = elem.text.strip()
                        if phone_text and re.search(r'\d{3}', phone_text):
                            result["phone_numbers"].append(phone_text)
                except:
                    continue

            return result if result["name"] else None

        except Exception as e:
            logger.warning(f"Error parsing Nuwber result card details: {e}")
            return None
