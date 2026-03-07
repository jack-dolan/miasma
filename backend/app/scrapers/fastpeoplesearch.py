"""
FastPeopleSearch scraper — Camoufox + JSON-LD extraction.

Uses Camoufox (antidetect Firefox via Playwright) to bypass Cloudflare Turnstile
and DataDome, then extracts structured person data from JSON-LD blocks embedded
in the page source. No DOM parsing needed.

Browser session is reusable: call open() once, then search() multiple times,
then close(). Or use scrape() for one-shot lookups that manage the session
automatically.

Requires: camoufox, xvfb (Linux)
"""

import asyncio
import html
import json
import logging
import random
import re
from typing import Dict, List, Optional, Any

from app.scrapers.result import ScraperResult

logger = logging.getLogger(__name__)


class FastPeopleSearchScraper:
    """
    Scraper for FastPeopleSearch.com using Camoufox.

    Doesn't inherit from BaseScraper because it uses Playwright (via Camoufox)
    instead of Selenium. Outputs ScraperResult for compatibility with the rest
    of the pipeline.

    Usage (batch):
        scraper = FastPeopleSearchScraper()
        await scraper.open()
        result1 = await scraper.search("John", "Smith", city="Boston", state="MA")
        result2 = await scraper.search("Jane", "Doe", state="NY")
        await scraper.close()

    Usage (one-shot):
        scraper = FastPeopleSearchScraper()
        result = await scraper.scrape("John", "Smith", city="Boston", state="MA")
    """

    BASE_URL = "https://www.fastpeoplesearch.com"
    CHALLENGE_TIMEOUT = 20  # seconds to wait for Turnstile
    PAGE_LOAD_TIMEOUT = 30000  # ms
    MAX_RETRIES = 2  # retries per search if Turnstile/load fails
    REQUEST_DELAY_MIN = 3.0  # min seconds between requests (batch mode)
    REQUEST_DELAY_MAX = 7.0  # max seconds between requests (batch mode)

    def __init__(self):
        self.source_name = "FastPeopleSearch"
        self._browser = None
        self._context_manager = None
        self._page = None
        self._request_count = 0

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def open(self):
        """
        Launch browser and create a reusable page.

        Call this once before doing multiple search() calls. The browser
        stays open until close() is called, so Turnstile only needs to be
        solved on the first request (cookies persist across navigations).
        """
        if self._browser:
            return  # already open

        from camoufox.async_api import AsyncCamoufox

        self._context_manager = AsyncCamoufox(
            headless="virtual",
            humanize=True,
        )
        self._browser = await self._context_manager.__aenter__()
        self._page = await self._browser.new_page()
        self._request_count = 0
        logger.info("FastPeopleSearch: browser session opened")

    async def close(self):
        """Close the browser session."""
        if self._context_manager:
            try:
                await self._context_manager.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            finally:
                self._browser = None
                self._context_manager = None
                self._page = None
        logger.info("FastPeopleSearch: browser session closed")

    # ------------------------------------------------------------------
    # URL building
    # ------------------------------------------------------------------

    def _build_search_url(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
    ) -> str:
        """Build search URL. Format: /name/first-last_city-state"""
        name_slug = f"{first_name}-{last_name}".lower().replace(" ", "-")

        if city and state:
            location_slug = f"{city}-{state}".lower().replace(" ", "-")
            return f"{self.BASE_URL}/name/{name_slug}_{location_slug}"
        elif state:
            location_slug = state.lower().replace(" ", "-")
            return f"{self.BASE_URL}/name/{name_slug}_{location_slug}"
        else:
            return f"{self.BASE_URL}/name/{name_slug}"

    # ------------------------------------------------------------------
    # Cloudflare Turnstile
    # ------------------------------------------------------------------

    async def _solve_turnstile(self, page) -> bool:
        """
        Attempt to solve Cloudflare Turnstile challenge.

        Turnstile renders in an iframe from challenges.cloudflare.com.
        Clicking the iframe body is usually enough with Camoufox since
        it passes the browser fingerprint checks.

        Returns True if challenge was solved or wasn't present.
        """
        title = await page.title()

        if "just a moment" not in title.lower() and "security challenge" not in title.lower():
            return True  # no challenge

        logger.info("Cloudflare Turnstile detected, solving...")

        # Wait for the Turnstile iframe to load
        await page.wait_for_timeout(3000)

        # Find and click the Turnstile frame
        clicked = False
        for frame in page.frames:
            if "challenges.cloudflare.com" in frame.url:
                try:
                    await frame.click("body")
                    clicked = True
                    logger.info("Clicked Turnstile frame")
                except Exception as e:
                    logger.warning(f"Failed to click Turnstile frame: {e}")
                break

        if not clicked:
            logger.warning("No Turnstile frame found, waiting anyway...")

        # Poll for resolution
        checks = self.CHALLENGE_TIMEOUT // 2
        for i in range(checks):
            await page.wait_for_timeout(2000)
            title = await page.title()
            if "just a moment" not in title.lower() and "security challenge" not in title.lower():
                logger.info(f"Turnstile solved in {(i+1)*2}s")
                return True

        logger.error(f"Turnstile not solved after {self.CHALLENGE_TIMEOUT}s")
        return False

    # ------------------------------------------------------------------
    # Data extraction
    # ------------------------------------------------------------------

    def _extract_jsonld_persons(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Extract Person objects from JSON-LD script tags.

        FPS embeds JSON-LD blocks in <script type="application/ld+json"> tags.
        The Person block is a list of Person objects with:
          - name, additionalName (aliases)
          - HomeLocation (addresses with street/city/state/zip/geo)
          - telephone (phone numbers)
          - relatedTo (relatives)
        """
        jsonld_blocks = re.findall(
            r'<script\s+type="application/ld\+json">(.*?)</script>',
            html_content, re.DOTALL
        )

        persons = []
        for block_str in jsonld_blocks:
            try:
                data = json.loads(block_str)
            except json.JSONDecodeError:
                continue

            # Could be a single object or a list
            items = data if isinstance(data, list) else [data]

            for item in items:
                if item.get("@type") == "Person":
                    persons.append(item)

        return persons

    def _extract_gresults(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Extract gResults from the wam.init() call.

        gResults is HTML-encoded JSON inside a JS string property:
            gResults:'[{&quot;firstname&quot;:...}]'

        Contains age, dob_month, tahoeId (for matching to JSON-LD persons),
        and basic name/location fields.
        """
        # Match the gResults property value (HTML-encoded JSON string)
        match = re.search(
            r"gResults:'(\[.*?\])'",
            html_content, re.DOTALL
        )
        if not match:
            return []

        encoded = match.group(1)
        decoded = html.unescape(encoded)

        try:
            return json.loads(decoded)
        except json.JSONDecodeError:
            logger.warning("Failed to parse gResults JSON")
            return []

    def _merge_person_data(
        self,
        jsonld_persons: List[Dict[str, Any]],
        gresults: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Merge JSON-LD Person data with gResults to get age/DOB.

        Matching is done via tahoeId — gResults has tahoeId, JSON-LD has
        it embedded in the @id URL (e.g. /john-smith_id_G3008487962272741523).
        """
        # Build a lookup from tahoeId -> gResults entry
        gr_by_id = {}
        for gr in gresults:
            tid = gr.get("tahoeId", "")
            if tid:
                gr_by_id[tid] = gr

        results = []
        for person in jsonld_persons:
            normalized = self._normalize_person(person)

            # Try to find matching gResults entry
            person_id = person.get("@id", "")
            # Extract tahoeId from URL like: /john-smith_id_G3008487962272741523
            id_match = re.search(r'_id_(\S+)$', person_id)
            if id_match:
                tahoe_id = id_match.group(1)
                gr = gr_by_id.get(tahoe_id, {})
                if gr:
                    normalized["age"] = gr.get("age")
                    normalized["dob_month"] = gr.get("dob_month")

            results.append(normalized)

        return results

    def _normalize_person(self, person: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a JSON-LD Person into our standard profile format.

        Input (JSON-LD):
            name, HomeLocation[].address.{street,city,state,zip},
            telephone[], additionalName[], relatedTo[].name

        Output (our format):
            name, addresses[].{street,city,state,zip},
            phone_numbers[], aliases[], relatives[], age, dob_month
        """
        result = {
            "name": person.get("name"),
            "profile_url": person.get("url"),
            "addresses": [],
            "phone_numbers": [],
            "aliases": [],
            "relatives": [],
            "age": None,
            "dob_month": None,
        }

        # Addresses from HomeLocation
        for loc in person.get("HomeLocation", []):
            addr = loc.get("address", {})
            result["addresses"].append({
                "street": addr.get("streetAddress", ""),
                "city": addr.get("addressLocality", ""),
                "state": addr.get("addressRegion", ""),
                "zip": addr.get("postalCode", ""),
            })

        # Phone numbers
        result["phone_numbers"] = person.get("telephone", [])

        # Aliases from additionalName
        result["aliases"] = person.get("additionalName", [])

        # Relatives from relatedTo
        for rel in person.get("relatedTo", []):
            if isinstance(rel, dict):
                name = rel.get("name", "")
                if name:
                    result["relatives"].append(name)
            elif isinstance(rel, str):
                result["relatives"].append(rel)

        return result

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def _rate_limit(self):
        """Random delay between requests to avoid detection."""
        if self._request_count > 0:
            delay = random.uniform(self.REQUEST_DELAY_MIN, self.REQUEST_DELAY_MAX)
            logger.debug(f"Rate limit: waiting {delay:.1f}s")
            await asyncio.sleep(delay)
        self._request_count += 1

    async def search(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        age: Optional[int] = None,
    ) -> ScraperResult:
        """
        Search FastPeopleSearch for a person.

        Requires an open browser session (call open() first, or use scrape()
        for automatic session management).
        """
        if not self._page:
            return ScraperResult(
                source=self.source_name,
                success=False,
                error="Browser not open — call open() first",
            )

        url = self._build_search_url(first_name, last_name, city, state)
        logger.info(f"FastPeopleSearch: searching {url}")

        last_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                # Rate limit between requests
                await self._rate_limit()

                # Navigate
                response = await self._page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.PAGE_LOAD_TIMEOUT,
                )

                if not response:
                    last_error = "No response from page"
                    logger.warning(f"Attempt {attempt}: {last_error}")
                    continue

                # Handle Cloudflare Turnstile
                if not await self._solve_turnstile(self._page):
                    last_error = "Failed to solve Cloudflare challenge"
                    logger.warning(f"Attempt {attempt}: {last_error}")
                    # Reload on retry — get a fresh challenge
                    continue

                # Small delay for page to settle after challenge
                await self._page.wait_for_timeout(1500)

                # Get page content
                html_content = await self._page.content()

                # Extract both data sources
                jsonld_persons = self._extract_jsonld_persons(html_content)
                gresults = self._extract_gresults(html_content)

                if not jsonld_persons:
                    # Could be a "no results" page — not an error
                    logger.info("No Person data found in JSON-LD")
                    return ScraperResult(
                        source=self.source_name,
                        success=True,
                        data={"results": [], "total_found": 0},
                    )

                # Merge JSON-LD with gResults for age/DOB
                results = self._merge_person_data(jsonld_persons, gresults)

                logger.info(
                    f"FastPeopleSearch: {len(results)} results "
                    f"({len(gresults)} with age data)"
                )
                return ScraperResult(
                    source=self.source_name,
                    success=True,
                    data={
                        "results": results,
                        "total_found": len(results),
                    },
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Attempt {attempt}/{self.MAX_RETRIES} failed: {e}",
                    exc_info=(attempt == self.MAX_RETRIES),
                )

        # All retries exhausted
        return ScraperResult(
            source=self.source_name,
            success=False,
            error=f"Failed after {self.MAX_RETRIES} attempts: {last_error}",
        )

    async def scrape(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        age: Optional[int] = None,
    ) -> ScraperResult:
        """
        One-shot search with automatic session management.

        Opens a browser, does the search, closes the browser.
        For multiple lookups, use open()/search()/close() instead.
        """
        try:
            await self.open()
            return await self.search(
                first_name=first_name,
                last_name=last_name,
                city=city,
                state=state,
                age=age,
            )
        finally:
            await self.close()

    def __repr__(self) -> str:
        return f"<FastPeopleSearchScraper(source={self.source_name})>"
