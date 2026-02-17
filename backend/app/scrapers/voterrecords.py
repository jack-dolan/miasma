"""
VoterRecords.com scraper implementation
"""

import logging
import re
from typing import Dict, List, Optional, Any

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

from app.scrapers.base import BaseScraper, ScraperResult

logger = logging.getLogger(__name__)


class VoterRecordsScraper(BaseScraper):
    """Scraper for VoterRecords.com - voter registration data"""

    BASE_URL = "https://voterrecords.com"

    def _build_search_url(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None
    ) -> str:
        """Build the search URL for VoterRecords name lookup"""
        first = first_name.strip().capitalize()
        last = last_name.strip().capitalize()

        if state:
            # some state-filtered searches use a different path
            state_slug = state.strip().lower()
            return f"{self.BASE_URL}/voters/{first}-{last}/{state_slug}/"
        else:
            return f"{self.BASE_URL}/voters/{first}-{last}/"

    async def search(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        age: Optional[int] = None
    ) -> ScraperResult:
        """Perform search on VoterRecords"""

        try:
            search_url = self._build_search_url(first_name, last_name, city, state)
            logger.info(f"VoterRecords: Searching at {search_url}")

            if not await self.safe_get(search_url):
                return ScraperResult(
                    source=self.source_name,
                    success=False,
                    error="Failed to load search page"
                )

            await self.random_delay(2, 4)

            # block/protection detection
            page_title = self.driver.title.lower()
            page_source_lower = self.driver.page_source[:5000].lower()

            if "just a moment" in page_title or "cloudflare" in page_source_lower:
                logger.warning("VoterRecords: Cloudflare protection detected, waiting...")
                await self.random_delay(5, 10)

            if "blocked" in page_title or "access denied" in page_source_lower:
                logger.error("VoterRecords: Access blocked")
                return ScraperResult(
                    source=self.source_name,
                    success=False,
                    error="Access blocked by site"
                )

            if "captcha" in page_source_lower:
                logger.error("VoterRecords: CAPTCHA detected")
                return ScraperResult(
                    source=self.source_name,
                    success=False,
                    error="CAPTCHA detected"
                )

            data = self.parse_results()

            if not data or not data.get("results"):
                try:
                    self.driver.save_screenshot("voterrecords_debug.png")
                    with open("voterrecords_page.html", "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                    logger.info("Saved VoterRecords debug screenshot and HTML")
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
            logger.error(f"VoterRecords search failed: {e}", exc_info=True)
            return ScraperResult(
                source=self.source_name,
                success=False,
                error=str(e)
            )

    def parse_results(self) -> Dict[str, Any]:
        """Parse voter record search results using BeautifulSoup"""

        results = []

        try:
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # VoterRecords uses various structures depending on the page.
            # Try table rows first (common for voter data), then card/div layouts.
            result_selectors = [
                "table.table tbody tr",
                "div.voter-record",
                "div.record",
                "div[class*='voter']",
                "div[class*='result']",
                "div.card",
                "div.list-group-item",
                "li.list-group-item",
                "article",
                "section.voter",
            ]

            result_cards = []
            used_selector = None
            for selector in result_selectors:
                cards = soup.select(selector)
                if cards:
                    result_cards = cards
                    used_selector = selector
                    logger.info(f"VoterRecords: Found {len(cards)} results with selector: {selector}")
                    break

            # fallback: look for links to individual voter pages
            if not result_cards:
                voter_links = soup.select("a[href*='/voter/']")
                if not voter_links:
                    voter_links = soup.select("a[href*='/voters/']")
                if voter_links:
                    logger.info(f"VoterRecords: Found {len(voter_links)} voter links (fallback)")
                    seen_parents = set()
                    for link in voter_links[:20]:
                        parent = link.find_parent(['div', 'li', 'tr', 'article', 'section'])
                        if parent:
                            parent_id = id(parent)
                            if parent_id not in seen_parents:
                                seen_parents.add(parent_id)
                                result_cards.append(parent)

            is_table = used_selector and "tr" in used_selector

            for card in result_cards[:20]:
                try:
                    if is_table:
                        result_data = self._parse_table_row(card, soup)
                    else:
                        result_data = self._parse_voter_card(card)

                    if result_data and result_data.get("name"):
                        results.append(result_data)
                except Exception as e:
                    logger.warning(f"VoterRecords: Error parsing record: {e}")
                    continue

            logger.info(f"VoterRecords: Parsed {len(results)} voter records")
            return {
                "results": results,
                "total_found": len(results)
            }

        except Exception as e:
            logger.error(f"VoterRecords: Error parsing results: {e}", exc_info=True)
            return {"results": [], "total_found": 0}

    def _parse_table_row(self, row, soup) -> Optional[Dict[str, Any]]:
        """Parse a table row as a voter record"""

        result = {
            "name": None,
            "age": None,
            "location": None,
            "addresses": [],
            "phone_numbers": [],
            "emails": [],
            "relatives": [],
            "profile_url": None,
            "party": None,
            "voter_status": None
        }

        try:
            cells = row.select("td")
            if not cells:
                return None

            row_text = row.get_text(separator=' ', strip=True)

            # grab the link if there is one
            link = row.select_one("a[href*='/voter/']") or row.select_one("a")
            if link:
                result["name"] = link.get_text(strip=True)
                href = link.get('href')
                if href:
                    if not href.startswith('http'):
                        href = f"{self.BASE_URL}{href}"
                    result["profile_url"] = href

            # if no link, first cell is usually the name
            if not result["name"] and cells:
                result["name"] = cells[0].get_text(strip=True)

            # try to extract structured data from table columns
            # common column orders: Name, Address/City, State, Zip, Party, Status
            # or: Name, Age, Location, Party
            # We do best-effort based on content of each cell
            for cell in cells:
                cell_text = cell.get_text(strip=True)
                if not cell_text:
                    continue

                # party affiliation: usually short strings like "Democrat", "Republican", etc.
                if cell_text in ('Democrat', 'Republican', 'Libertarian', 'Green',
                                 'Independent', 'No Party', 'Unaffiliated',
                                 'DEM', 'REP', 'LIB', 'GRN', 'IND', 'NPA', 'UNA'):
                    result["party"] = cell_text

                # voter status
                elif cell_text.lower() in ('active', 'inactive', 'purged', 'suspended',
                                            'cancelled', 'pending'):
                    result["voter_status"] = cell_text

                # zip code (5 digits, not an age)
                elif re.match(r'^\d{5}(-\d{4})?$', cell_text):
                    # it's a zip; append to address if we have one
                    pass

                # state abbreviation (2 uppercase letters, not a party code)
                elif (re.match(r'^[A-Z]{2}$', cell_text)
                      and cell_text not in ('DEM', 'REP', 'LIB', 'GRN', 'IND', 'NPA', 'UNA')):
                    if not result["location"]:
                        result["location"] = cell_text

            # build address from row text if we can
            addr_match = re.search(
                r'(\d+\s+[A-Za-z0-9\s.]+(?:St|Ave|Blvd|Dr|Rd|Ln|Ct|Way|Pl|Cir|Pkwy|Hwy)[.,]?\s*'
                r'(?:[A-Za-z\s]+,\s*)?[A-Z]{2}(?:\s+\d{5})?)',
                row_text, re.IGNORECASE
            )
            if addr_match:
                addr = addr_match.group(1).strip()
                if addr not in result["addresses"]:
                    result["addresses"].append(addr)

            # location from city/state pattern
            if not result["location"]:
                loc_match = re.search(r'([A-Za-z\s]+),\s*([A-Z]{2})\b', row_text)
                if loc_match:
                    city = loc_match.group(1).strip()
                    if city and len(city) > 1:
                        result["location"] = f"{city}, {loc_match.group(2)}"

            # age from text
            age_match = re.search(r'(?:age|Age)[:\s]*(\d+)', row_text)
            if age_match:
                result["age"] = int(age_match.group(1))
            else:
                age_match = re.search(r'\b(\d{2,3})\s*years?\s*old\b', row_text, re.IGNORECASE)
                if age_match:
                    result["age"] = int(age_match.group(1))

            return result if result["name"] else None

        except Exception as e:
            logger.warning(f"VoterRecords: Error parsing table row: {e}")
            return None

    def _parse_voter_card(self, card) -> Optional[Dict[str, Any]]:
        """Parse a div/card-based voter record"""

        result = {
            "name": None,
            "age": None,
            "location": None,
            "addresses": [],
            "phone_numbers": [],
            "emails": [],
            "relatives": [],
            "profile_url": None,
            "party": None,
            "voter_status": None
        }

        try:
            card_text = card.get_text(separator=' ', strip=True)

            # -- Name --
            name_selectors = [
                "h2 a", "h3 a", "h4 a", ".name a", ".name", "a.name",
                "strong a", "a[href*='/voter/']", "a[href*='/voters/']",
                ".card-title", "b"
            ]
            for sel in name_selectors:
                elem = card.select_one(sel)
                if elem and elem.get_text(strip=True):
                    raw_name = elem.get_text(strip=True)
                    if len(raw_name) < 3:
                        continue
                    result["name"] = raw_name
                    href = elem.get('href')
                    if not href:
                        link = elem.find('a')
                        if link:
                            href = link.get('href')
                    if href:
                        if not href.startswith('http'):
                            href = f"{self.BASE_URL}{href}"
                        result["profile_url"] = href
                    break

            # -- Party affiliation --
            party_selectors = [".party", "[class*='party']", "[class*='affiliation']"]
            for sel in party_selectors:
                elem = card.select_one(sel)
                if elem:
                    result["party"] = elem.get_text(strip=True)
                    break

            if not result["party"]:
                # look for party keywords in the text
                party_match = re.search(
                    r'\b(Democrat|Republican|Libertarian|Green|Independent|'
                    r'No\s*Party|Unaffiliated|NPA|DEM|REP|LIB|GRN|IND)\b',
                    card_text, re.IGNORECASE
                )
                if party_match:
                    result["party"] = party_match.group(1).strip()

            # -- Voter status --
            status_selectors = [".status", "[class*='status']", ".voter-status"]
            for sel in status_selectors:
                elem = card.select_one(sel)
                if elem:
                    result["voter_status"] = elem.get_text(strip=True)
                    break

            if not result["voter_status"]:
                status_match = re.search(
                    r'\b(Active|Inactive|Purged|Suspended|Cancelled|Pending)\b',
                    card_text, re.IGNORECASE
                )
                if status_match:
                    result["voter_status"] = status_match.group(1).strip()

            # -- Address --
            addr_selectors = [".address", "[class*='address']", ".location", "[class*='location']"]
            for sel in addr_selectors:
                elems = card.select(sel)
                for elem in elems:
                    addr = elem.get_text(strip=True)
                    if addr and len(addr) > 5 and addr not in result["addresses"]:
                        result["addresses"].append(addr)

            # fallback: look for street address patterns in text
            if not result["addresses"]:
                addr_matches = re.findall(
                    r'(\d+\s+[A-Za-z0-9\s.]+(?:St|Ave|Blvd|Dr|Rd|Ln|Ct|Way|Pl|Cir|Pkwy|Hwy)[.,]?'
                    r'(?:\s+(?:Apt|Unit|#)\s*\S+)?'
                    r'(?:\s*,?\s*[A-Za-z\s]+,\s*[A-Z]{2})?'
                    r'(?:\s+\d{5}(?:-\d{4})?)?)',
                    card_text, re.IGNORECASE
                )
                for addr in addr_matches:
                    addr = addr.strip()
                    if addr and addr not in result["addresses"]:
                        result["addresses"].append(addr)

            # -- Location --
            if not result["location"]:
                loc_match = re.search(r'([A-Za-z\s]+),\s*([A-Z]{2})\b', card_text)
                if loc_match:
                    city = loc_match.group(1).strip()
                    city = re.sub(r'^(View\s+)', '', city, flags=re.IGNORECASE).strip()
                    if city and len(city) > 1:
                        result["location"] = f"{city}, {loc_match.group(2)}"

            if not result["location"] and result["addresses"]:
                loc_match = re.search(r'([A-Za-z\s]+),\s*([A-Z]{2})', result["addresses"][0])
                if loc_match:
                    result["location"] = f"{loc_match.group(1).strip()}, {loc_match.group(2)}"

            # -- Age --
            age_selectors = [".age", "[class*='age']"]
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

            # -- Phone --
            phone_matches = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', card_text)
            for phone in phone_matches:
                if phone not in result["phone_numbers"]:
                    result["phone_numbers"].append(phone)

            # -- Email --
            email_matches = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', card_text)
            for email in email_matches:
                if email not in result["emails"]:
                    result["emails"].append(email)

            return result if result["name"] else None

        except Exception as e:
            logger.warning(f"VoterRecords: Error parsing voter card: {e}")
            return None
