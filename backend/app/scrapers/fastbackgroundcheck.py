"""
FastBackgroundCheck.com scraper implementation
"""

import logging
import re
from typing import Dict, List, Optional, Any

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

from app.scrapers.base import BaseScraper, ScraperResult

logger = logging.getLogger(__name__)


class FastBackgroundCheckScraper(BaseScraper):
    """Scraper for FastBackgroundCheck.com"""

    BASE_URL = "https://www.fastbackgroundcheck.com"

    def _build_search_url(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None
    ) -> str:
        """
        Build the search URL for FastBackgroundCheck.
        Format: /people/Lastname/First-Last
        With location: /people/Lastname/First-Last/City-ST
        """
        first = first_name.strip().capitalize()
        last = last_name.strip().capitalize()
        name_slug = f"{first}-{last}"

        if city and state:
            city_slug = city.strip().replace(" ", "-").title()
            state_slug = state.strip().upper()
            return f"{self.BASE_URL}/people/{last}/{name_slug}/{city_slug}-{state_slug}"
        else:
            return f"{self.BASE_URL}/people/{last}/{name_slug}"

    async def search(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        age: Optional[int] = None
    ) -> ScraperResult:
        """Perform search on FastBackgroundCheck"""

        try:
            search_url = self._build_search_url(first_name, last_name, city, state)
            logger.info(f"FastBackgroundCheck: Searching at {search_url}")

            if not await self.safe_get(search_url):
                return ScraperResult(
                    source=self.source_name,
                    success=False,
                    error="Failed to load search page"
                )

            await self.random_delay(2, 4)

            # block detection
            page_title = self.driver.title.lower()
            page_source_lower = self.driver.page_source[:5000].lower()

            if "just a moment" in page_title or "cloudflare" in page_source_lower:
                logger.warning("FastBackgroundCheck: Cloudflare protection detected, waiting...")
                await self.random_delay(5, 10)

            if "blocked" in page_title or "access denied" in page_source_lower:
                logger.error("FastBackgroundCheck: Access blocked")
                return ScraperResult(
                    source=self.source_name,
                    success=False,
                    error="Access blocked by site"
                )

            if "captcha" in page_source_lower:
                logger.error("FastBackgroundCheck: CAPTCHA detected")
                return ScraperResult(
                    source=self.source_name,
                    success=False,
                    error="CAPTCHA detected"
                )

            data = self.parse_results()

            if not data or not data.get("results"):
                try:
                    self.driver.save_screenshot("fastbackgroundcheck_debug.png")
                    with open("fastbackgroundcheck_page.html", "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                    logger.info("Saved FastBackgroundCheck debug screenshot and HTML")
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
            logger.error(f"FastBackgroundCheck search failed: {e}", exc_info=True)
            return ScraperResult(
                source=self.source_name,
                success=False,
                error=str(e)
            )

    def parse_results(self) -> Dict[str, Any]:
        """Parse search results from FastBackgroundCheck using BeautifulSoup"""

        results = []

        try:
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # FastBackgroundCheck is server-rendered with directory-style pages.
            # Try several common selectors for person listing cards.
            result_selectors = [
                "div.card",
                "div.record",
                "div[class*='person']",
                "div[class*='result']",
                "div.listing",
                "div.people-card",
                "a.list-group-item",
                "div.list-group-item",
                "li.list-group-item",
                "tr.record-row",
                "article",
            ]

            result_cards = []
            for selector in result_selectors:
                cards = soup.select(selector)
                if cards:
                    result_cards = cards
                    logger.info(f"FastBackgroundCheck: Found {len(cards)} results with selector: {selector}")
                    break

            # if none of the above matched, try a broader approach:
            # look for repeated sibling elements that contain name-like links
            if not result_cards:
                # look for links that point to person profile pages
                person_links = soup.select("a[href*='/people/']")
                if person_links:
                    logger.info(f"FastBackgroundCheck: Found {len(person_links)} person links (fallback)")
                    for link in person_links[:15]:
                        parent = link.find_parent(['div', 'li', 'article', 'tr'])
                        if parent and parent not in result_cards:
                            result_cards.append(parent)

            for card in result_cards[:15]:
                try:
                    result_data = self._parse_person_card(card, soup)
                    if result_data and result_data.get("name"):
                        results.append(result_data)
                except Exception as e:
                    logger.warning(f"FastBackgroundCheck: Error parsing card: {e}")
                    continue

            logger.info(f"FastBackgroundCheck: Parsed {len(results)} person records")
            return {
                "results": results,
                "total_found": len(results)
            }

        except Exception as e:
            logger.error(f"FastBackgroundCheck: Error parsing results: {e}", exc_info=True)
            return {"results": [], "total_found": 0}

    def _parse_person_card(self, card, soup) -> Optional[Dict[str, Any]]:
        """Parse an individual person card from FastBackgroundCheck"""

        result = {
            "name": None,
            "age": None,
            "location": None,
            "addresses": [],
            "phone_numbers": [],
            "emails": [],
            "relatives": [],
            "profile_url": None
        }

        try:
            card_text = card.get_text(separator=' ', strip=True)

            # -- Name --
            name_selectors = [
                "h2 a", "h3 a", "a.name", ".name", "strong a",
                "a[href*='/people/']", ".card-title", "h4 a"
            ]
            for sel in name_selectors:
                elem = card.select_one(sel)
                if elem and elem.get_text(strip=True):
                    raw_name = elem.get_text(strip=True)
                    # skip if it looks like a nav link or generic text
                    if len(raw_name) < 3 or raw_name.lower() in ('view', 'more', 'search'):
                        continue
                    result["name"] = raw_name
                    href = elem.get('href')
                    if href:
                        if not href.startswith('http'):
                            href = f"{self.BASE_URL}{href}"
                        result["profile_url"] = href
                    break

            # -- Age --
            # commonly shown as "Age 45" or "45 years old" or just a number near name
            age_selectors = [".age", "span.age", ".person-age", "[class*='age']"]
            for sel in age_selectors:
                elem = card.select_one(sel)
                if elem:
                    age_match = re.search(r'(\d+)', elem.get_text(strip=True))
                    if age_match:
                        result["age"] = int(age_match.group(1))
                        break

            if not result["age"]:
                age_match = re.search(r'(?:age|Age)[:\s]*(\d+)', card_text)
                if age_match:
                    result["age"] = int(age_match.group(1))
                else:
                    age_match = re.search(r'(\d+)\s*years?\s*old', card_text, re.IGNORECASE)
                    if age_match:
                        result["age"] = int(age_match.group(1))

            # check for "Name, Age" format in the name field
            if not result["age"] and result["name"]:
                name_age = re.match(r'^(.+?),\s*(?:age\s+)?(\d{2,3})$', result["name"], re.IGNORECASE)
                if name_age:
                    result["name"] = name_age.group(1).strip()
                    result["age"] = int(name_age.group(2))

            # -- Location / Addresses --
            addr_selectors = [
                ".address", ".location", "[class*='address']",
                "[class*='location']", ".city-state", "span.addr"
            ]
            for sel in addr_selectors:
                elems = card.select(sel)
                for elem in elems:
                    addr = elem.get_text(strip=True)
                    if addr and len(addr) > 5 and addr not in result["addresses"]:
                        result["addresses"].append(addr)

            # fallback: pick up "City, ST" or "City, ST ZIP" from card text
            if not result["addresses"]:
                addr_matches = re.findall(
                    r'(\d+\s+[A-Za-z0-9\s.]+,\s*[A-Za-z\s]+,\s*[A-Z]{2}(?:\s+\d{5})?)',
                    card_text
                )
                for addr in addr_matches:
                    addr = addr.strip()
                    if addr and addr not in result["addresses"]:
                        result["addresses"].append(addr)

            # set location from first address
            if not result["location"]:
                loc_match = re.search(r'([A-Za-z\s]+),\s*([A-Z]{2})\b', card_text)
                if loc_match:
                    city = loc_match.group(1).strip()
                    # clean noise before city name
                    city = re.sub(r'^(View\s+Profile\s*)', '', city, flags=re.IGNORECASE).strip()
                    if city and len(city) > 1:
                        result["location"] = f"{city}, {loc_match.group(2)}"

            # -- Phone numbers --
            phone_selectors = [".phone", "[class*='phone']", "a[href^='tel:']"]
            for sel in phone_selectors:
                elems = card.select(sel)
                for elem in elems:
                    phone = elem.get_text(strip=True)
                    if phone and re.search(r'\d{3}', phone) and phone not in result["phone_numbers"]:
                        result["phone_numbers"].append(phone)

            if not result["phone_numbers"]:
                phone_matches = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', card_text)
                for phone in phone_matches:
                    if phone not in result["phone_numbers"]:
                        result["phone_numbers"].append(phone)

            # -- Relatives --
            rel_selectors = [
                ".relatives a", "[class*='relative'] a", "[class*='associate'] a",
                ".related a", "a[href*='/people/']"
            ]
            for sel in rel_selectors:
                elems = card.select(sel)
                for elem in elems:
                    rel_name = elem.get_text(strip=True)
                    # skip if it's the same as the main person or too short
                    if (rel_name and len(rel_name) > 2
                            and rel_name != result["name"]
                            and rel_name not in result["relatives"]):
                        result["relatives"].append(rel_name)
                if result["relatives"]:
                    break

            return result if result["name"] else None

        except Exception as e:
            logger.warning(f"FastBackgroundCheck: Error parsing card details: {e}")
            return None
