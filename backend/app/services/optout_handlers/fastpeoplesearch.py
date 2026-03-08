"""
FastPeopleSearch opt-out handler.

Flow:
1. Search for target person.
2. Find best matching result card.
3. Click remove/opt-out action.
4. Confirm removal request on the follow-up screen.
"""

import re
from typing import Any, Dict, Optional

from app.services.optout_handler import BaseOptoutHandler, OptoutResult


class FastPeopleSearchOptoutHandler(BaseOptoutHandler):
    """Automates FastPeopleSearch remove-record flow."""

    BASE_URL = "https://www.fastpeoplesearch.com"
    SEARCH_PATH = "/name"

    def __init__(self):
        super().__init__("fastpeoplesearch")

    def _build_search_url(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
    ) -> str:
        first_slug = first_name.strip().lower().replace(" ", "-")
        last_slug = last_name.strip().lower().replace(" ", "-")
        name_slug = f"{first_slug}-{last_slug}"

        if city and state:
            location_slug = f"{city.strip().lower().replace(' ', '-')}-{state.strip().lower()}"
            return f"{self.BASE_URL}{self.SEARCH_PATH}/{name_slug}_{location_slug}"
        if state:
            return f"{self.BASE_URL}{self.SEARCH_PATH}/{name_slug}_{state.strip().lower()}"
        return f"{self.BASE_URL}{self.SEARCH_PATH}/{name_slug}"

    def _extract_location(self, profile: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
        addresses = profile.get("addresses") or []
        if not addresses:
            return None, None

        first = addresses[0] if isinstance(addresses[0], dict) else {}
        city = first.get("city")
        state = first.get("state")
        return city, state

    def _candidate_score(
        self,
        text: str,
        first_name: str,
        last_name: str,
        city: Optional[str],
        state: Optional[str],
        age: Optional[int],
    ) -> int:
        normalized = " ".join(text.lower().split())
        score = 0

        if first_name.lower() in normalized:
            score += 3
        if last_name.lower() in normalized:
            score += 3
        if city and city.lower() in normalized:
            score += 2
        if state and state.lower() in normalized:
            score += 2
        if age and str(age) in normalized:
            score += 1
        return score

    async def _find_best_result_card(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str],
        state: Optional[str],
        age: Optional[int],
    ):
        card_selectors = [
            ".card",
            ".card-content",
            ".result-card",
            "[class*='record']",
            "div:has(a[href*='remove'])",
        ]

        best_card = None
        best_score = -1

        for selector in card_selectors:
            cards = self._page.locator(selector)
            count = await cards.count()
            for i in range(count):
                card = cards.nth(i)
                text = await card.inner_text()
                score = self._candidate_score(text, first_name, last_name, city, state, age)
                if score > best_score:
                    best_score = score
                    best_card = card
            if best_card is not None and best_score >= 6:
                break

        return best_card, best_score

    async def _click_remove_action(self, card) -> bool:
        selectors = [
            "a:has-text('Remove')",
            "a:has-text('Opt Out')",
            "a[href*='remove']",
            "a[href*='optout']",
            "button:has-text('Remove')",
            "button:has-text('Opt Out')",
        ]
        for selector in selectors:
            loc = card.locator(selector).first
            if await loc.count():
                await loc.click()
                return True
        return False

    async def _complete_confirmation(self, profile: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        email = (profile.get("emails") or [None])[0]
        if email:
            email_fields = self._page.locator("input[type='email'], input[name*='email']")
            if await email_fields.count():
                await email_fields.first.fill(email)

        checkbox = self._page.locator(
            "input[type='checkbox'], [role='checkbox'], label:has-text('I am')"
        ).first
        if await checkbox.count():
            try:
                await checkbox.click()
            except Exception:
                pass

        submit_buttons = self._page.locator(
            "button:has-text('Submit'), button:has-text('Confirm'), "
            "button:has-text('Remove'), input[type='submit']"
        )
        if await submit_buttons.count():
            await submit_buttons.first.click()
            await self._random_delay(2, 4)

        body_text = (await self._page.content()).lower()
        success_markers = [
            "request has been submitted",
            "your record is being removed",
            "we have received your request",
            "opt out request received",
        ]
        removed = any(marker in body_text for marker in success_markers)

        reference_match = re.search(r"(request|confirmation)\s*(id|number)?[:#]?\s*([a-z0-9\-]{6,})", body_text)
        reference_id = reference_match.group(3) if reference_match else None
        return removed, reference_id

    async def perform_optout(self, profile: Dict[str, Any]) -> OptoutResult:
        first_name = (profile.get("first_name") or "").strip()
        last_name = (profile.get("last_name") or "").strip()
        age = profile.get("age")
        city, state = self._extract_location(profile)

        if not first_name or not last_name:
            return OptoutResult(
                site=self.site_name,
                success=False,
                removed=False,
                error="Profile must include first_name and last_name",
            )

        search_url = self._build_search_url(first_name, last_name, city=city, state=state)
        await self._goto(search_url)

        if not await self._solve_turnstile_if_present():
            return OptoutResult(
                site=self.site_name,
                success=False,
                removed=False,
                error="Failed Cloudflare challenge",
                details={"search_url": search_url},
            )

        card, score = await self._find_best_result_card(first_name, last_name, city, state, age)
        if card is None or score < 4:
            return OptoutResult(
                site=self.site_name,
                success=False,
                removed=False,
                error="No sufficiently matching record found",
                details={"search_url": search_url, "best_score": score},
            )

        clicked = await self._click_remove_action(card)
        if not clicked:
            return OptoutResult(
                site=self.site_name,
                success=False,
                removed=False,
                error="Matched record found but no remove action available",
                details={"search_url": search_url, "best_score": score},
            )

        await self._random_delay(2, 4)
        removed, reference_id = await self._complete_confirmation(profile)
        return OptoutResult(
            site=self.site_name,
            success=removed,
            removed=removed,
            reference_id=reference_id,
            error=None if removed else "Removal confirmation was not detected",
            details={"search_url": search_url, "best_score": score},
        )
