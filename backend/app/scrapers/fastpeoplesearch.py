"""
FastPeopleSearch scraper implementation
"""

import logging
import re
from typing import Dict, List, Optional, Any

from selenium.webdriver.common.by import By

from app.scrapers.base import BaseScraper, ScraperResult

logger = logging.getLogger(__name__)


class FastPeopleSearchScraper(BaseScraper):
    """Scraper for FastPeopleSearch.com"""

    BASE_URL = "https://www.fastpeoplesearch.com"

    def _build_search_url(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None
    ) -> str:
        """Build the search URL based on available parameters"""
        # FastPeopleSearch uses hyphenated names in URL
        name_slug = f"{first_name}-{last_name}".lower().replace(" ", "-")

        if city and state:
            # Format: /name/city-state
            location_slug = f"{city}-{state}".lower().replace(" ", "-")
            return f"{self.BASE_URL}/name/{name_slug}_{location_slug}"
        else:
            # Format: /name
            return f"{self.BASE_URL}/name/{name_slug}"

    async def search(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        age: Optional[int] = None
    ) -> ScraperResult:
        """Perform search on FastPeopleSearch"""

        try:
            search_url = self._build_search_url(first_name, last_name, city, state)
            logger.info(f"FastPeopleSearch: Searching at {search_url}")

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
            if "just a moment" in page_title or "blocked" in page_title:
                logger.warning("FastPeopleSearch: Cloudflare protection detected")
                # Wait longer and retry
                await self.random_delay(5, 10)

            # Check if we got a results page or a profile page
            current_url = self.driver.current_url

            # Parse results
            data = self.parse_results()

            if not data or (not data.get("results") and not data.get("profile")):
                # Save debug info
                try:
                    self.driver.save_screenshot("fastpeoplesearch_debug.png")
                    with open("fastpeoplesearch_page.html", "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                    logger.info("DEBUG: Saved screenshot and HTML for inspection")
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
            logger.error(f"FastPeopleSearch search failed: {e}", exc_info=True)
            return ScraperResult(
                source=self.source_name,
                success=False,
                error=str(e)
            )

    def parse_results(self) -> Dict[str, Any]:
        """Parse search results from FastPeopleSearch"""

        results = []

        try:
            # Check if this is a search results page (multiple people)
            # or a direct profile page (single person)

            # Try to find result cards (search results page)
            result_cards = self.find_elements_safe(
                By.CSS_SELECTOR,
                "div.card.card-block, div.people-list-item, div[data-link]"
            )

            if result_cards:
                logger.info(f"Found {len(result_cards)} result cards")
                for card in result_cards:
                    try:
                        result_data = self._parse_result_card(card)
                        if result_data:
                            results.append(result_data)
                    except Exception as e:
                        logger.warning(f"Error parsing result card: {e}")
                        continue

            # If no result cards, try parsing as a profile page
            if not results:
                profile_data = self._parse_profile_page()
                if profile_data and profile_data.get("name"):
                    return {
                        "profile": profile_data,
                        "results": [profile_data],
                        "total_found": 1
                    }

            return {
                "results": results,
                "total_found": len(results)
            }

        except Exception as e:
            logger.error(f"Error parsing results: {e}", exc_info=True)
            return {"results": [], "total_found": 0}

    def _parse_result_card(self, card) -> Optional[Dict[str, Any]]:
        """Parse individual result card from search results"""

        result = {
            "name": None,
            "age": None,
            "location": None,
            "addresses": [],
            "phone_numbers": [],
            "profile_url": None
        }

        try:
            # Try to find name link
            name_elem = card.find_element(By.CSS_SELECTOR, "a.link-to-details, h2 a, .name a")
            if name_elem:
                result["name"] = name_elem.text.strip()
                result["profile_url"] = name_elem.get_attribute("href")

            # Try to find age
            age_elem = self._find_element_in_card(card, ".age, span:contains('Age')")
            if age_elem:
                age_text = age_elem.text.strip()
                age_match = re.search(r'\d+', age_text)
                if age_match:
                    result["age"] = int(age_match.group())

            # Try to find location
            location_elem = self._find_element_in_card(card, ".location, .city-state, .address")
            if location_elem:
                result["location"] = location_elem.text.strip()

            return result if result["name"] else None

        except Exception as e:
            logger.warning(f"Error parsing result card details: {e}")
            return None

    def _find_element_in_card(self, card, selector: str):
        """Try multiple selectors to find an element"""
        for sel in selector.split(", "):
            try:
                elem = card.find_element(By.CSS_SELECTOR, sel.strip())
                if elem:
                    return elem
            except:
                continue
        return None

    def _parse_profile_page(self) -> Optional[Dict[str, Any]]:
        """Parse a direct profile page"""

        result = {
            "name": None,
            "age": None,
            "location": None,
            "addresses": [],
            "phone_numbers": [],
            "relatives": [],
            "associates": []
        }

        try:
            # Parse header - format: "Name in City, State"
            header = self.find_element_safe(By.ID, "details-header")
            if header:
                header_text = header.text.strip()
                if " in " in header_text:
                    name_part, location_part = header_text.split(" in ", 1)
                    result["name"] = name_part.strip()
                    result["location"] = location_part.strip()
                else:
                    result["name"] = header_text

            # Parse age - format: "Age 47"
            age_header = self.find_element_safe(By.ID, "age-header")
            if age_header:
                age_text = age_header.text.strip()
                age_match = re.search(r'\d+', age_text)
                if age_match:
                    result["age"] = int(age_match.group())

            # Parse current address
            current_address_section = self.find_element_safe(By.ID, "current_address_section")
            if current_address_section:
                address_links = current_address_section.find_elements(By.TAG_NAME, "a")
                for link in address_links:
                    addr = link.text.strip()
                    if addr and addr not in result["addresses"]:
                        result["addresses"].append(addr)

            # Parse previous addresses
            prev_address_section = self.find_element_safe(By.ID, "past_address_section")
            if prev_address_section:
                address_links = prev_address_section.find_elements(By.TAG_NAME, "a")
                for link in address_links:
                    addr = link.text.strip()
                    if addr and addr not in result["addresses"]:
                        result["addresses"].append(addr)

            # Parse phone numbers
            phone_section = self.find_element_safe(By.ID, "phone_number_section")
            if phone_section:
                phone_links = phone_section.find_elements(By.TAG_NAME, "a")
                for link in phone_links:
                    phone = link.text.strip()
                    if phone and re.search(r'\d{3}', phone):
                        result["phone_numbers"].append(phone)

            # Parse relatives
            relatives_section = self.find_element_safe(By.ID, "relatives_section")
            if relatives_section:
                relative_links = relatives_section.find_elements(By.CSS_SELECTOR, "a[href*='/name/']")
                for link in relative_links:
                    name = link.text.strip()
                    if name:
                        result["relatives"].append(name)

            # Parse associates
            associates_section = self.find_element_safe(By.ID, "associates_section")
            if associates_section:
                associate_links = associates_section.find_elements(By.CSS_SELECTOR, "a[href*='/name/']")
                for link in associate_links:
                    name = link.text.strip()
                    if name:
                        result["associates"].append(name)

            return result if result["name"] else None

        except Exception as e:
            logger.error(f"Error parsing profile page: {e}", exc_info=True)
            return None
