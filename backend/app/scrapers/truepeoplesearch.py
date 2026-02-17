"""
TruePeopleSearch scraper implementation
"""

import logging
from typing import Dict, List, Optional, Any
from urllib.parse import quote

from selenium.webdriver.common.by import By

from app.scrapers.base import BaseScraper, ScraperResult

logger = logging.getLogger(__name__)


class TruePeopleSearchScraper(BaseScraper):
    """Scraper for TruePeopleSearch.com"""
    
    BASE_URL = "https://www.truepeoplesearch.com"
    
    async def search(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        age: Optional[int] = None
    ) -> ScraperResult:
        """Perform search on TruePeopleSearch"""
        
        try:
            # Build search URL
            search_query = f"{first_name} {last_name}"
            if city and state:
                search_query += f" {city} {state}"
            
            encoded_query = quote(search_query)
            search_url = f"{self.BASE_URL}/results?name={encoded_query}"
            
            logger.info(f"TruePeopleSearch: Searching for {search_query}")
            
            # Navigate to search page
            if not await self.safe_get(search_url):
                return ScraperResult(
                    source=self.source_name,
                    success=False,
                    error="Failed to load search page"
                )
            
            # Wait for results to load
            await self.random_delay(2, 4)
            
            # DEBUG: Save screenshot and page source
            try:
                self.driver.save_screenshot("truepeoplesearch_debug.png")
                with open("truepeoplesearch_page.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                logger.info("DEBUG: Saved screenshot and HTML for inspection")
            except Exception as e:
                logger.warning(f"Could not save debug files: {e}")
            
            # Parse results
            data = self.parse_results()
            
            if not data or not data.get("results"):
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
            logger.error(f"TruePeopleSearch search failed: {e}", exc_info=True)
            return ScraperResult(
                source=self.source_name,
                success=False,
                error=str(e)
            )
    
    def parse_results(self) -> Dict[str, Any]:
        """Parse search results from TruePeopleSearch"""
        
        results = []
        
        try:
            # Find all result cards
            result_cards = self.find_elements_safe(
                By.CSS_SELECTOR,
                "div.card.card-block.shadow-form.card-summary"
            )
            
            logger.info(f"Found {len(result_cards)} result cards")
            
            for card in result_cards:
                try:
                    result_data = self._parse_result_card(card)
                    if result_data:
                        results.append(result_data)
                except Exception as e:
                    logger.warning(f"Error parsing result card: {e}")
                    continue
            
            return {
                "results": results,
                "total_found": len(results)
            }
            
        except Exception as e:
            logger.error(f"Error parsing results: {e}", exc_info=True)
            return {"results": [], "total_found": 0}
    
    def _parse_result_card(self, card) -> Optional[Dict[str, Any]]:
        """Parse individual result card"""
        
        result = {
            "name": None,
            "age": None,
            "addresses": [],
            "phone_numbers": [],
            "relatives": [],
            "associates": []
        }
        
        try:
            # Extract name
            name_elem = card.find_element(By.CSS_SELECTOR, "h2.h4")
            if name_elem:
                result["name"] = name_elem.text.strip()
            
            # Extract age
            age_elem = card.find_element(By.CSS_SELECTOR, "span.content-label")
            if age_elem and "Age" in age_elem.text:
                age_text = age_elem.find_element(By.XPATH, "following-sibling::span").text
                try:
                    result["age"] = int(age_text.strip())
                except (ValueError, AttributeError):
                    pass
            
            # Extract addresses
            address_section = self._find_section(card, "Current Address")
            if address_section:
                addresses = self._extract_addresses(address_section)
                result["addresses"].extend(addresses)
            
            # Extract previous addresses
            prev_address_section = self._find_section(card, "Previous Addresses")
            if prev_address_section:
                addresses = self._extract_addresses(prev_address_section)
                result["addresses"].extend(addresses)
            
            # Extract phone numbers
            phone_section = self._find_section(card, "Phone Numbers")
            if phone_section:
                phones = self._extract_phones(phone_section)
                result["phone_numbers"].extend(phones)
            
            # Extract relatives
            relatives_section = self._find_section(card, "Relatives")
            if relatives_section:
                relatives = self._extract_names_list(relatives_section)
                result["relatives"].extend(relatives)
            
            # Extract associates
            associates_section = self._find_section(card, "Associates")
            if associates_section:
                associates = self._extract_names_list(associates_section)
                result["associates"].extend(associates)
            
            return result if result["name"] else None
            
        except Exception as e:
            logger.warning(f"Error parsing result card details: {e}")
            return None
    
    def _find_section(self, card, section_title: str):
        """Find a section within a result card by title"""
        try:
            sections = card.find_elements(By.CSS_SELECTOR, "div.row")
            for section in sections:
                label = section.find_element(By.CSS_SELECTOR, "span.content-label")
                if label and section_title.lower() in label.text.lower():
                    return section
        except Exception:
            pass
        return None
    
    def _extract_addresses(self, section) -> List[str]:
        """Extract addresses from a section"""
        addresses = []
        try:
            address_links = section.find_elements(By.CSS_SELECTOR, "a")
            for link in address_links:
                address = link.text.strip()
                if address:
                    addresses.append(address)
        except Exception as e:
            logger.debug(f"Error extracting addresses: {e}")
        return addresses
    
    def _extract_phones(self, section) -> List[str]:
        """Extract phone numbers from a section"""
        phones = []
        try:
            phone_links = section.find_elements(By.CSS_SELECTOR, "a")
            for link in phone_links:
                phone = link.text.strip()
                if phone:
                    phones.append(phone)
        except Exception as e:
            logger.debug(f"Error extracting phones: {e}")
        return phones
    
    def _extract_names_list(self, section) -> List[str]:
        """Extract list of names from a section"""
        names = []
        try:
            name_links = section.find_elements(By.CSS_SELECTOR, "a")
            for link in name_links:
                name = link.text.strip()
                if name:
                    names.append(name)
        except Exception as e:
            logger.debug(f"Error extracting names: {e}")
        return names