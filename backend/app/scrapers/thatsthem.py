"""
ThatsThem.com scraper implementation
"""

import logging
import re
from typing import Dict, List, Optional, Any

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

from app.scrapers.base import BaseScraper, ScraperResult

logger = logging.getLogger(__name__)


class ThatsThemScraper(BaseScraper):
    """Scraper for ThatsThem.com"""

    BASE_URL = "https://thatsthem.com"

    def _build_search_url(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None
    ) -> str:
        first = first_name.strip().capitalize()
        last = last_name.strip().capitalize()
        url = f"{self.BASE_URL}/name/{first}-{last}"
        if city and state:
            city_formatted = city.strip().replace(" ", "-")
            url += f"/{city_formatted}-{state.upper()}"
        return url

    async def search(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        age: Optional[int] = None
    ) -> ScraperResult:
        try:
            search_url = self._build_search_url(first_name, last_name, city, state)
            logger.info(f"ThatsThem: Searching at {search_url}")

            if not await self.safe_get(search_url):
                return ScraperResult(
                    source=self.source_name,
                    success=False,
                    error="Failed to load search page"
                )

            await self.random_delay(2, 4)

            # Check for challenge/captcha - retry once if hit
            page_source = self.driver.page_source.lower()
            if "captcha" in page_source or "recaptcha" in page_source:
                logger.warning("ThatsThem: Challenge detected, retrying...")
                await self.random_delay(3, 6)
                if not await self.safe_get(search_url):
                    return ScraperResult(
                        source=self.source_name,
                        success=False,
                        error="Failed to reload after challenge"
                    )
                await self.random_delay(2, 4)
                page_source = self.driver.page_source.lower()
                if "captcha" in page_source or "recaptcha" in page_source:
                    logger.error("ThatsThem: CAPTCHA persists after retry")
                    return ScraperResult(
                        source=self.source_name,
                        success=False,
                        error="CAPTCHA detected"
                    )

            data = self.parse_results()

            if not data or not data.get("results"):
                try:
                    self.driver.save_screenshot("thatsthem_debug.png")
                    with open("thatsthem_page.html", "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                    logger.info("Saved ThatsThem debug screenshot and HTML")
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
            logger.error(f"ThatsThem search failed: {e}", exc_info=True)
            return ScraperResult(
                source=self.source_name,
                success=False,
                error=str(e)
            )

    def parse_results(self) -> Dict[str, Any]:
        results = []

        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            records = soup.select("div.record")

            if not records:
                logger.info("ThatsThem: No div.record elements found")
                return {"results": [], "total_found": 0}

            logger.info(f"ThatsThem: Found {len(records)} records")

            for record in records[:10]:
                try:
                    parsed = self._parse_record(record)
                    if parsed and parsed.get("name"):
                        results.append(parsed)
                except Exception as e:
                    logger.warning(f"Error parsing ThatsThem record: {e}")
                    continue

            logger.info(f"ThatsThem: Parsed {len(results)} person records")
            return {"results": results, "total_found": len(results)}

        except Exception as e:
            logger.error(f"Error parsing ThatsThem results: {e}", exc_info=True)
            return {"results": [], "total_found": 0}

    def _parse_record(self, record) -> Optional[Dict[str, Any]]:
        result = {
            "name": None,
            "age": None,
            "location": None,
            "addresses": [],
            "phone_numbers": [],
            "emails": [],
            "relatives": [],
            "profile_url": None,
        }

        try:
            # Name
            name_el = record.select_one("div.name")
            if name_el:
                result["name"] = name_el.get_text(strip=True)

            # Location (lives in)
            resides_el = record.select_one("div.resides")
            if resides_el:
                loc_link = resides_el.select_one("a.web")
                if loc_link:
                    result["location"] = loc_link.get_text(strip=True)

            # Addresses (current + previous)
            for addr_el in record.select("div.location div.address"):
                street_el = addr_el.select_one(".street")
                city_el = addr_el.select_one(".city")
                state_el = addr_el.select_one(".state")
                zip_el = addr_el.select_one(".zip")

                parts = []
                if street_el:
                    parts.append(street_el.get_text(strip=True))
                city_parts = []
                if city_el:
                    city_parts.append(city_el.get_text(strip=True))
                if state_el:
                    city_parts.append(state_el.get_text(strip=True))
                if zip_el:
                    city_parts.append(zip_el.get_text(strip=True))
                if city_parts:
                    parts.append(", ".join(city_parts))

                addr_str = " ".join(parts)
                if addr_str and addr_str not in result["addresses"]:
                    result["addresses"].append(addr_str)

            # Phone numbers
            for phone_el in record.select("li.phone span.number"):
                number = phone_el.get_text(strip=True)
                if number and number not in result["phone_numbers"]:
                    result["phone_numbers"].append(number)

            # Email addresses
            for email_el in record.select("li.email span.inbox"):
                email = email_el.get_text(strip=True)
                if email and "@" in email and email not in result["emails"]:
                    result["emails"].append(email)

            # Relatives / family
            for rel_el in record.select("li.relative"):
                rel_name = rel_el.get_text(strip=True)
                if rel_name and rel_name not in result["relatives"]:
                    result["relatives"].append(rel_name)

            # Profile URL from record ID
            record_id = record.get("id")
            if record_id and result["name"]:
                name_slug = result["name"].replace(" ", "-")
                result["profile_url"] = f"https://thatsthem.com/name/{name_slug}#{record_id}"

            return result if result["name"] else None

        except Exception as e:
            logger.warning(f"Error parsing ThatsThem record details: {e}")
            return None
