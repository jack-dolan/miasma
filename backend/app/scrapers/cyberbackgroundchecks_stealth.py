"""
CyberBackgroundChecks.com scraper using SeleniumBase UC Mode.

Identical logic to the standard CyberBackgroundChecks scraper but uses
StealthScraper as its base class for bypassing Cloudflare/bot detection.
"""

import logging
import re
from typing import Dict, List, Optional, Any

from selenium.webdriver.common.by import By

from app.scrapers.stealth_base import StealthScraper
from app.scrapers.base import ScraperResult

logger = logging.getLogger(__name__)


class CyberBackgroundChecksStealthScraper(StealthScraper):
    """Scraper for CyberBackgroundChecks.com using UC Mode"""

    BASE_URL = "https://www.cyberbackgroundchecks.com"

    def _build_search_url(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None
    ) -> str:
        """Build the search URL based on available parameters"""
        first = first_name.capitalize()
        last = last_name.capitalize()

        if state:
            return f"{self.BASE_URL}/people/{first}/{last}/{state.upper()}"
        else:
            return f"{self.BASE_URL}/people/{first}/{last}"

    async def search(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        age: Optional[int] = None
    ) -> ScraperResult:
        """Perform search on CyberBackgroundChecks"""

        try:
            search_url = self._build_search_url(first_name, last_name, city, state)
            logger.info(f"CyberBackgroundChecks (stealth): Searching at {search_url}")

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
                logger.warning("CyberBackgroundChecks (stealth): Cloudflare protection detected, waiting...")
                await self.random_delay(5, 10)

                # Re-check after waiting
                page_title = self.driver.title.lower()
                page_source = self.driver.page_source.lower()

            if "blocked" in page_title or "access denied" in page_source:
                logger.error("CyberBackgroundChecks (stealth): Access blocked")
                return ScraperResult(
                    source=self.source_name,
                    success=False,
                    error="Access blocked by site"
                )

            # Parse results
            data = self.parse_results()

            if not data or not data.get("results"):
                try:
                    self.driver.save_screenshot("cyberbackgroundchecks_stealth_debug.png")
                    with open("cyberbackgroundchecks_stealth_page.html", "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                    logger.info("DEBUG: Saved stealth CyberBackgroundChecks screenshot and HTML")
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
            logger.error(f"CyberBackgroundChecks (stealth) search failed: {e}", exc_info=True)
            return ScraperResult(
                source=self.source_name,
                success=False,
                error=str(e)
            )

    def parse_results(self) -> Dict[str, Any]:
        """Parse search results from CyberBackgroundChecks"""

        results = []

        try:
            # Try multiple selectors for result cards
            result_selectors = [
                "div.card-body",
                "div[class*='person']",
                "div[class*='result']",
                "div.person-card",
                "a[href*='/person/']",
                "tr.person-row",
                "div.list-group-item"
            ]

            result_cards = []
            for selector in result_selectors:
                cards = self.find_elements_safe(By.CSS_SELECTOR, selector)
                if cards:
                    result_cards = cards
                    logger.info(f"Found {len(cards)} results with selector: {selector}")
                    break

            # Also try finding by link patterns
            if not result_cards:
                links = self.find_elements_safe(By.CSS_SELECTOR, "a[href*='/people/']")
                if links:
                    result_cards = links
                    logger.info(f"Found {len(links)} person links")

            for card in result_cards[:10]:  # Limit to first 10
                try:
                    result_data = self._parse_result_card(card)
                    if result_data and result_data.get("name"):
                        results.append(result_data)
                except Exception as e:
                    logger.warning(f"Error parsing CyberBackgroundChecks result card: {e}")
                    continue

            return {
                "results": results,
                "total_found": len(results)
            }

        except Exception as e:
            logger.error(f"Error parsing CyberBackgroundChecks results: {e}", exc_info=True)
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
            # If card is a link itself, get its text and href
            if card.tag_name == "a":
                result["name"] = card.text.strip()
                result["profile_url"] = card.get_attribute("href")
            else:
                # Try to find name in child elements
                name_selectors = ["h2", "h3", "h4", ".name", "a[href*='/people/']", ".card-title", "strong"]
                for sel in name_selectors:
                    try:
                        elem = card.find_element(By.CSS_SELECTOR, sel)
                        if elem and elem.text.strip():
                            text = elem.text.strip()
                            if len(text) > 2 and len(text) < 100 and not text.startswith("http"):
                                result["name"] = text
                                href = elem.get_attribute("href")
                                if href:
                                    result["profile_url"] = href
                                break
                    except:
                        continue

            # Try to find age
            try:
                card_text = card.text
                age_match = re.search(r'(?:age|Age|AGE)[:\s]*(\d+)', card_text)
                if age_match:
                    result["age"] = int(age_match.group(1))
                else:
                    age_match = re.search(r'\b([2-9]\d)\b', card_text)
                    if age_match:
                        potential_age = int(age_match.group(1))
                        if 18 <= potential_age <= 100:
                            result["age"] = potential_age
            except:
                pass

            # Try to find location/address
            location_selectors = [".address", ".location", "span[class*='address']", "small", ".text-muted"]
            for sel in location_selectors:
                try:
                    elems = card.find_elements(By.CSS_SELECTOR, sel)
                    for elem in elems:
                        text = elem.text.strip()
                        if text and (re.search(r'\b[A-Z]{2}\b', text) or re.search(r'\b\d{5}\b', text)):
                            result["location"] = text
                            result["addresses"].append(text)
                            break
                except:
                    continue

            # Try to find phone
            try:
                card_text = card.text
                phone_matches = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', card_text)
                for phone in phone_matches:
                    if phone not in result["phone_numbers"]:
                        result["phone_numbers"].append(phone)
            except:
                pass

            return result if result["name"] else None

        except Exception as e:
            logger.warning(f"Error parsing CyberBackgroundChecks result card details: {e}")
            return None
