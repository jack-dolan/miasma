"""
USPhoneBook.com scraper implementation
"""

import logging
import re
from typing import Dict, List, Optional, Any

from selenium.webdriver.common.by import By

from app.scrapers.base import BaseScraper, ScraperResult

logger = logging.getLogger(__name__)


class USPhoneBookScraper(BaseScraper):
    """Scraper for USPhoneBook.com"""

    BASE_URL = "https://www.usphonebook.com"

    def _build_search_url(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None
    ) -> str:
        """Build the search URL based on available parameters"""
        # USPhoneBook uses path format: /firstname-lastname/state/
        name_slug = f"{first_name}-{last_name}".lower()

        if state:
            return f"{self.BASE_URL}/{name_slug}/{state.lower()}/"
        else:
            return f"{self.BASE_URL}/{name_slug}/"

    async def search(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        age: Optional[int] = None
    ) -> ScraperResult:
        """Perform search on USPhoneBook"""

        try:
            search_url = self._build_search_url(first_name, last_name, city, state)
            logger.info(f"USPhoneBook: Searching at {search_url}")

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
                logger.warning("USPhoneBook: Cloudflare protection detected, waiting...")
                await self.random_delay(5, 10)

            if "blocked" in page_title or "access denied" in page_source:
                logger.error("USPhoneBook: Access blocked")
                return ScraperResult(
                    source=self.source_name,
                    success=False,
                    error="Access blocked by site"
                )

            # Parse results
            data = self.parse_results()

            if not data or not data.get("results"):
                try:
                    self.driver.save_screenshot("usphonebook_debug.png")
                    with open("usphonebook_page.html", "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                    logger.info("DEBUG: Saved USPhoneBook screenshot and HTML")
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
            logger.error(f"USPhoneBook search failed: {e}", exc_info=True)
            return ScraperResult(
                source=self.source_name,
                success=False,
                error=str(e)
            )

    def parse_results(self) -> Dict[str, Any]:
        """Parse search results from USPhoneBook"""

        results = []

        try:
            # Try multiple selectors for result cards
            result_selectors = [
                "div.ls_contacts",
                "div[class*='contact']",
                "div[class*='result']",
                "div[class*='person']",
                "a[href*='/phone/']",
                "div.card"
            ]

            result_cards = []
            for selector in result_selectors:
                cards = self.find_elements_safe(By.CSS_SELECTOR, selector)
                if cards:
                    result_cards = cards
                    logger.info(f"Found {len(cards)} results with selector: {selector}")
                    break

            for card in result_cards[:10]:
                try:
                    result_data = self._parse_result_card(card)
                    if result_data and result_data.get("name"):
                        results.append(result_data)
                except Exception as e:
                    logger.warning(f"Error parsing USPhoneBook result card: {e}")
                    continue

            return {
                "results": results,
                "total_found": len(results)
            }

        except Exception as e:
            logger.error(f"Error parsing USPhoneBook results: {e}", exc_info=True)
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
            # Find name
            name_selectors = ["h2 a", "h3 a", ".name", "a[href*='/phone/']", "strong"]
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

            # Find age from text
            try:
                card_text = card.text
                age_match = re.search(r'(?:age|Age)[:\s]*(\d+)', card_text)
                if age_match:
                    result["age"] = int(age_match.group(1))
            except:
                pass

            # Find phone
            try:
                card_text = card.text
                phone_matches = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', card_text)
                for phone in phone_matches:
                    if phone not in result["phone_numbers"]:
                        result["phone_numbers"].append(phone)
            except:
                pass

            # Find address/location
            try:
                card_text = card.text
                # Look for city, state pattern
                location_match = re.search(r'([A-Za-z\s]+),\s*([A-Z]{2})\b', card_text)
                if location_match:
                    result["location"] = f"{location_match.group(1)}, {location_match.group(2)}"
                    result["addresses"].append(result["location"])
            except:
                pass

            return result if result["name"] else None

        except Exception as e:
            logger.warning(f"Error parsing USPhoneBook result card details: {e}")
            return None
