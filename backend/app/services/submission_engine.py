"""
Submission engine for pushing poisoned profiles into upstream data sources.

Data brokers scrape their records from public profile sites, directories,
and marketing databases. Instead of targeting broker opt-out forms (which only
remove existing records), we inject fake data into the same upstream sources
that brokers pull from. This causes the fake records to propagate naturally
through the broker ecosystem.

Site-specific submitters inherit from BaseSubmitter and implement submit()
to handle each upstream source's signup or submission flow.
"""

import logging
import uuid
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

from app.scrapers.base import BaseScraper, ScraperResult

logger = logging.getLogger(__name__)


@dataclass
class SubmissionResult:
    site: str
    success: bool
    reference_id: Optional[str] = None
    error: Optional[str] = None
    submitted_at: Optional[datetime] = None
    profile_snapshot: Optional[dict] = field(default_factory=dict)


class BaseSubmitter(BaseScraper):
    """
    Base class for site-specific submission handlers.
    Inherits driver management from BaseScraper; search/parse are no-ops.
    """

    def __init__(self):
        super().__init__()
        self.site_name = self.__class__.__name__.replace("Submitter", "").lower()
        # override source_name so logging uses the submitter name
        self.source_name = self.site_name

    # -- BaseScraper abstract methods (unused by submitters) --

    async def search(self, first_name, last_name, city=None, state=None, age=None):
        return ScraperResult(source=self.source_name, success=False, error="Not a scraper")

    def parse_results(self):
        return {}

    # -- Submitter interface --

    @abstractmethod
    async def submit(self, profile: dict) -> SubmissionResult:
        """Submit a fake profile to an upstream data source."""
        pass

    async def execute(self, profile: dict) -> SubmissionResult:
        """Full workflow: init driver -> submit -> close driver."""
        try:
            if not await self.initialize_driver():
                return SubmissionResult(
                    site=self.site_name,
                    success=False,
                    error="Driver init failed",
                )
            return await self.submit(profile)
        except Exception as e:
            logger.error(f"{self.site_name}: submission failed: {e}", exc_info=True)
            return SubmissionResult(
                site=self.site_name,
                success=False,
                error=str(e),
            )
        finally:
            await self.close_driver()

    def _fill_field(self, by: By, value: str, text: str) -> bool:
        """Find a field and type into it. Returns True if successful."""
        el = self.find_element_safe(by, value)
        if not el:
            return False
        el.clear()
        el.send_keys(text)
        return True

    def _click(self, by: By, value: str) -> bool:
        """Find an element and click it. Returns True if successful."""
        el = self.find_element_safe(by, value)
        if not el:
            return False
        el.click()
        return True

    def _select_by_text(self, by: By, value: str, text: str) -> bool:
        """Find a <select> and choose an option by visible text."""
        el = self.find_element_safe(by, value)
        if not el:
            return False
        try:
            Select(el).select_by_visible_text(text)
            return True
        except Exception:
            return False

    def _select_by_value(self, by: By, selector: str, val: str) -> bool:
        """Find a <select> and choose an option by value attribute."""
        el = self.find_element_safe(by, selector)
        if not el:
            return False
        try:
            Select(el).select_by_value(val)
            return True
        except Exception:
            return False


class AboutMeSubmitter(BaseSubmitter):
    """
    Creates a public profile on about.me.
    About.me profiles get indexed by search engines and scraped by brokers
    looking for name + location + employment data.
    """

    SIGNUP_URL = "https://about.me/signup"

    async def submit(self, profile: dict) -> SubmissionResult:
        first = profile.get("first_name", "")
        last = profile.get("last_name", "")
        email = (profile.get("emails") or [None])[0]
        employment = profile.get("employment", {})
        city = ""
        state = ""
        if profile.get("addresses"):
            addr = profile["addresses"][0]
            city = addr.get("city", "")
            state = addr.get("state", "")

        if not email:
            return SubmissionResult(
                site="aboutme", success=False, error="Email required for signup"
            )

        try:
            if not await self.safe_get(self.SIGNUP_URL):
                return SubmissionResult(
                    site="aboutme", success=False, error="Failed to load signup page"
                )

            await self.random_delay(2, 4)

            page_src = self.driver.page_source.lower()
            if "captcha" in page_src or "blocked" in page_src:
                return SubmissionResult(
                    site="aboutme", success=False, error="Bot detection triggered"
                )

            # fill signup form -- about.me uses a multi-step flow
            # step 1: name and email
            for sel in ["input[name='name']", "input#name", "input[placeholder*='name' i]"]:
                if self._fill_field(By.CSS_SELECTOR, sel, f"{first} {last}"):
                    break

            await self.random_delay(0.5, 1)

            for sel in ["input[name='email']", "input[type='email']",
                        "input[placeholder*='email' i]"]:
                if self._fill_field(By.CSS_SELECTOR, sel, email):
                    break

            await self.random_delay(0.5, 1)

            # password field
            for sel in ["input[name='password']", "input[type='password']",
                        "input[placeholder*='password' i]"]:
                # use a generated password - we don't need to keep it
                if self._fill_field(By.CSS_SELECTOR, sel, f"Px{uuid.uuid4().hex[:12]}!"):
                    break

            await self.random_delay(0.5, 1)

            # submit signup
            for sel in ["button[type='submit']", "input[type='submit']",
                        "button.signup-btn", "button[class*='submit']",
                        "button[class*='signup']", "button[class*='continue']"]:
                if self._click(By.CSS_SELECTOR, sel):
                    break

            await self.random_delay(3, 6)

            # step 2: fill profile details (bio, location, job)
            bio = f"{employment.get('title', 'Professional')} based in {city}, {state}."
            location = f"{city}, {state}" if city else state

            for sel in ["textarea[name='bio']", "textarea[name='headline']",
                        "textarea[placeholder*='bio' i]", "textarea"]:
                if self._fill_field(By.CSS_SELECTOR, sel, bio):
                    break

            await self.random_delay(0.5, 1)

            for sel in ["input[name='location']", "input[placeholder*='location' i]",
                        "input[name='city']"]:
                if self._fill_field(By.CSS_SELECTOR, sel, location):
                    break

            await self.random_delay(0.5, 1)

            if employment.get("title"):
                for sel in ["input[name='job_title']", "input[name='title']",
                            "input[placeholder*='title' i]", "input[placeholder*='job' i]"]:
                    if self._fill_field(By.CSS_SELECTOR, sel, employment["title"]):
                        break

            if employment.get("company"):
                for sel in ["input[name='company']", "input[name='organization']",
                            "input[placeholder*='company' i]"]:
                    if self._fill_field(By.CSS_SELECTOR, sel, employment["company"]):
                        break

            await self.random_delay(0.5, 1)

            # save profile
            for sel in ["button[type='submit']", "button[class*='save']",
                        "button[class*='continue']", "button[class*='done']",
                        "button[class*='finish']"]:
                if self._click(By.CSS_SELECTOR, sel):
                    break

            await self.random_delay(2, 4)

            ref_id = f"am-{uuid.uuid4().hex[:8]}"

            return SubmissionResult(
                site="aboutme",
                success=True,
                reference_id=ref_id,
                submitted_at=datetime.utcnow(),
                profile_snapshot=profile,
            )

        except Exception as e:
            return SubmissionResult(site="aboutme", success=False, error=str(e))


class GravatarSubmitter(BaseSubmitter):
    """
    Creates a Gravatar profile via the web interface.
    Gravatar profiles are publicly accessible via API and get pulled
    by people-search engines that index email-associated data.
    """

    SIGNUP_URL = "https://gravatar.com/connect/"

    async def submit(self, profile: dict) -> SubmissionResult:
        first = profile.get("first_name", "")
        last = profile.get("last_name", "")
        email = (profile.get("emails") or [None])[0]
        employment = profile.get("employment", {})
        city = ""
        state = ""
        if profile.get("addresses"):
            addr = profile["addresses"][0]
            city = addr.get("city", "")
            state = addr.get("state", "")

        if not email:
            return SubmissionResult(
                site="gravatar", success=False, error="Email required for signup"
            )

        try:
            if not await self.safe_get(self.SIGNUP_URL):
                return SubmissionResult(
                    site="gravatar", success=False, error="Failed to load signup page"
                )

            await self.random_delay(2, 4)

            # Gravatar signup goes through WordPress.com
            # step 1: create account
            for sel in ["input[name='email']", "input[type='email']", "input#email"]:
                if self._fill_field(By.CSS_SELECTOR, sel, email):
                    break

            await self.random_delay(0.5, 1)

            # click continue/next
            for sel in ["button[type='submit']", "button.button-primary",
                        "button[class*='continue']"]:
                if self._click(By.CSS_SELECTOR, sel):
                    break

            await self.random_delay(2, 4)

            # username step
            for sel in ["input[name='username']", "input#username"]:
                username = f"{first.lower()}{last.lower()}{random_suffix()}"
                if self._fill_field(By.CSS_SELECTOR, sel, username):
                    break

            await self.random_delay(0.5, 1)

            # password step
            for sel in ["input[name='password']", "input[type='password']"]:
                if self._fill_field(By.CSS_SELECTOR, sel, f"Gx{uuid.uuid4().hex[:12]}!"):
                    break

            await self.random_delay(0.5, 1)

            for sel in ["button[type='submit']", "button.button-primary"]:
                if self._click(By.CSS_SELECTOR, sel):
                    break

            await self.random_delay(3, 6)

            # step 2: edit profile -- navigate to profile editor
            await self.safe_get("https://gravatar.com/profiles/edit")
            await self.random_delay(2, 3)

            # fill display name
            for sel in ["input[name='display_name']", "input[name='displayname']",
                        "input[placeholder*='name' i]"]:
                if self._fill_field(By.CSS_SELECTOR, sel, f"{first} {last}"):
                    break

            # fill bio/description
            bio = f"{employment.get('title', 'Professional')} in {city}, {state}."
            for sel in ["textarea[name='description']", "textarea[name='bio']",
                        "textarea[name='about']", "textarea"]:
                if self._fill_field(By.CSS_SELECTOR, sel, bio):
                    break

            # fill location
            for sel in ["input[name='location']", "input[placeholder*='location' i]"]:
                loc = f"{city}, {state}" if city else state
                if self._fill_field(By.CSS_SELECTOR, sel, loc):
                    break

            await self.random_delay(0.5, 1)

            # save
            for sel in ["button[type='submit']", "button[class*='save']",
                        "input[type='submit']"]:
                if self._click(By.CSS_SELECTOR, sel):
                    break

            await self.random_delay(2, 4)

            ref_id = f"gv-{uuid.uuid4().hex[:8]}"

            return SubmissionResult(
                site="gravatar",
                success=True,
                reference_id=ref_id,
                submitted_at=datetime.utcnow(),
                profile_snapshot=profile,
            )

        except Exception as e:
            return SubmissionResult(site="gravatar", success=False, error=str(e))


class LinktreeSubmitter(BaseSubmitter):
    """
    Creates a public Linktree page.
    Linktree pages are indexed by search engines and scraped by people-search
    aggregators looking for name + social links.
    """

    SIGNUP_URL = "https://linktr.ee/register"

    async def submit(self, profile: dict) -> SubmissionResult:
        first = profile.get("first_name", "")
        last = profile.get("last_name", "")
        email = (profile.get("emails") or [None])[0]
        employment = profile.get("employment", {})
        city = ""
        state = ""
        if profile.get("addresses"):
            addr = profile["addresses"][0]
            city = addr.get("city", "")
            state = addr.get("state", "")

        if not email:
            return SubmissionResult(
                site="linktree", success=False, error="Email required for signup"
            )

        try:
            if not await self.safe_get(self.SIGNUP_URL):
                return SubmissionResult(
                    site="linktree", success=False, error="Failed to load signup page"
                )

            await self.random_delay(2, 4)

            page_src = self.driver.page_source.lower()
            if "captcha" in page_src or "challenge" in page_src:
                return SubmissionResult(
                    site="linktree", success=False, error="Bot detection triggered"
                )

            # Linktree signup -- email, username, password flow
            for sel in ["input[name='email']", "input[type='email']", "input#email"]:
                if self._fill_field(By.CSS_SELECTOR, sel, email):
                    break

            await self.random_delay(0.5, 1)

            # username
            username = f"{first.lower()}.{last.lower()}{random_suffix()}"
            for sel in ["input[name='username']", "input#username",
                        "input[placeholder*='username' i]"]:
                if self._fill_field(By.CSS_SELECTOR, sel, username):
                    break

            await self.random_delay(0.5, 1)

            # password
            for sel in ["input[name='password']", "input[type='password']"]:
                if self._fill_field(By.CSS_SELECTOR, sel, f"Lx{uuid.uuid4().hex[:12]}!"):
                    break

            await self.random_delay(0.5, 1)

            # name field
            for sel in ["input[name='name']", "input[placeholder*='name' i]"]:
                if self._fill_field(By.CSS_SELECTOR, sel, f"{first} {last}"):
                    break

            await self.random_delay(0.5, 1)

            # submit signup
            for sel in ["button[type='submit']", "button[data-testid*='register']",
                        "button[class*='submit']", "button[class*='signup']"]:
                if self._click(By.CSS_SELECTOR, sel):
                    break

            await self.random_delay(3, 6)

            # after signup, fill bio and add links
            bio = f"{first} {last} - {employment.get('title', 'Professional')} in {city}, {state}"
            for sel in ["textarea[name='bio']", "textarea[placeholder*='bio' i]",
                        "textarea"]:
                if self._fill_field(By.CSS_SELECTOR, sel, bio):
                    break

            await self.random_delay(0.5, 1)

            # save / continue
            for sel in ["button[type='submit']", "button[class*='save']",
                        "button[class*='continue']", "button[class*='done']"]:
                if self._click(By.CSS_SELECTOR, sel):
                    break

            await self.random_delay(2, 4)

            ref_id = f"lt-{uuid.uuid4().hex[:8]}"

            return SubmissionResult(
                site="linktree",
                success=True,
                reference_id=ref_id,
                submitted_at=datetime.utcnow(),
                profile_snapshot=profile,
            )

        except Exception as e:
            return SubmissionResult(site="linktree", success=False, error=str(e))


class DirectorySubmitter(BaseSubmitter):
    """
    Submits profile info to free business and people directories.
    Targets sites like YellowPages free listing, Yelp business listing,
    and similar directories that data brokers scrape for phone/address data.
    """

    # rotate through multiple directory sites
    DIRECTORY_URLS = [
        "https://www.yellowpages.com/free-listing",
        "https://www.hotfrog.com/AddYourBusiness.aspx",
        "https://www.brownbook.net/add-business/",
    ]

    async def submit(self, profile: dict) -> SubmissionResult:
        first = profile.get("first_name", "")
        last = profile.get("last_name", "")
        email = (profile.get("emails") or [None])[0]
        phones = profile.get("phone_numbers", [])
        phone = phones[0].get("number", "") if phones else ""
        employment = profile.get("employment", {})

        street = ""
        city = ""
        state = ""
        zipcode = ""
        if profile.get("addresses"):
            addr = profile["addresses"][0]
            street = addr.get("street", "")
            city = addr.get("city", "")
            state = addr.get("state", "")
            zipcode = addr.get("zip", "")

        if not email:
            return SubmissionResult(
                site="directory", success=False, error="Email required for submission"
            )

        try:
            # try each directory until one works
            loaded = False
            for url in self.DIRECTORY_URLS:
                if await self.safe_get(url):
                    loaded = True
                    break

            if not loaded:
                return SubmissionResult(
                    site="directory", success=False, error="Could not load any directory site"
                )

            await self.random_delay(2, 4)

            page_src = self.driver.page_source.lower()
            if "captcha" in page_src or "blocked" in page_src:
                return SubmissionResult(
                    site="directory", success=False, error="Bot detection triggered"
                )

            # business/listing name
            biz_name = employment.get("company", f"{first} {last} Services")
            for sel in ["input[name='businessName']", "input[name='business_name']",
                        "input[name='companyName']", "input[name='company']",
                        "input[name='name']", "input[placeholder*='business' i]",
                        "input[placeholder*='company' i]"]:
                if self._fill_field(By.CSS_SELECTOR, sel, biz_name):
                    break

            await self.random_delay(0.3, 0.8)

            # contact name
            for sel in ["input[name='contactName']", "input[name='contact_name']",
                        "input[name='fullName']", "input[placeholder*='contact' i]",
                        "input[placeholder*='your name' i]"]:
                if self._fill_field(By.CSS_SELECTOR, sel, f"{first} {last}"):
                    break

            await self.random_delay(0.3, 0.8)

            # address
            for sel in ["input[name='address']", "input[name='street']",
                        "input[name='address1']", "input[placeholder*='address' i]",
                        "input[placeholder*='street' i]"]:
                if self._fill_field(By.CSS_SELECTOR, sel, street):
                    break

            for sel in ["input[name='city']", "input[placeholder*='city' i]"]:
                if self._fill_field(By.CSS_SELECTOR, sel, city):
                    break

            # state - try select dropdown first, then text input
            for sel in ["select[name='state']", "select[name='region']"]:
                if self._select_by_value(By.CSS_SELECTOR, sel, state):
                    break
                if self._select_by_text(By.CSS_SELECTOR, sel, state):
                    break
            else:
                for sel in ["input[name='state']", "input[placeholder*='state' i]"]:
                    if self._fill_field(By.CSS_SELECTOR, sel, state):
                        break

            for sel in ["input[name='zip']", "input[name='zipcode']",
                        "input[name='postalCode']", "input[placeholder*='zip' i]"]:
                if self._fill_field(By.CSS_SELECTOR, sel, zipcode):
                    break

            await self.random_delay(0.3, 0.8)

            # phone
            if phone:
                for sel in ["input[name='phone']", "input[name='telephone']",
                            "input[type='tel']", "input[placeholder*='phone' i]"]:
                    if self._fill_field(By.CSS_SELECTOR, sel, phone):
                        break

            # email
            for sel in ["input[name='email']", "input[type='email']",
                        "input[placeholder*='email' i]"]:
                if self._fill_field(By.CSS_SELECTOR, sel, email):
                    break

            await self.random_delay(0.3, 0.8)

            # category / industry
            if employment.get("industry"):
                for sel in ["input[name='category']", "input[name='industry']",
                            "input[placeholder*='category' i]"]:
                    if self._fill_field(By.CSS_SELECTOR, sel, employment["industry"]):
                        break

            await self.random_delay(0.5, 1)

            # submit
            submitted = False
            for sel in ["button[type='submit']", "input[type='submit']",
                        "button[class*='submit']", "button[class*='add']",
                        "button.btn-primary"]:
                if self._click(By.CSS_SELECTOR, sel):
                    submitted = True
                    break

            if not submitted:
                try:
                    active = self.driver.switch_to.active_element
                    active.send_keys(Keys.RETURN)
                    submitted = True
                except Exception:
                    pass

            if not submitted:
                return SubmissionResult(
                    site="directory", success=False, error="Could not submit form"
                )

            await self.random_delay(3, 5)

            ref_id = f"dir-{uuid.uuid4().hex[:8]}"

            return SubmissionResult(
                site="directory",
                success=True,
                reference_id=ref_id,
                submitted_at=datetime.utcnow(),
                profile_snapshot=profile,
            )

        except Exception as e:
            return SubmissionResult(site="directory", success=False, error=str(e))


class MarketingFormSubmitter(BaseSubmitter):
    """
    Submits profile info to marketing data collection points --
    sweepstakes, survey forms, and newsletter signups that share data
    with broker data partners and marketing aggregators.
    """

    # rotate through forms that are known to share data widely
    FORM_URLS = [
        "https://www.pch.com/sweepstakes",
        "https://www.freebies.com/register",
    ]

    async def submit(self, profile: dict) -> SubmissionResult:
        first = profile.get("first_name", "")
        last = profile.get("last_name", "")
        email = (profile.get("emails") or [None])[0]
        phones = profile.get("phone_numbers", [])
        phone = phones[0].get("number", "") if phones else ""
        dob = profile.get("date_of_birth", "")

        street = ""
        city = ""
        state = ""
        zipcode = ""
        if profile.get("addresses"):
            addr = profile["addresses"][0]
            street = addr.get("street", "")
            city = addr.get("city", "")
            state = addr.get("state", "")
            zipcode = addr.get("zip", "")

        if not email:
            return SubmissionResult(
                site="marketing", success=False, error="Email required for submission"
            )

        try:
            loaded = False
            for url in self.FORM_URLS:
                if await self.safe_get(url):
                    loaded = True
                    break

            if not loaded:
                return SubmissionResult(
                    site="marketing", success=False, error="Could not load any form"
                )

            await self.random_delay(2, 4)

            page_src = self.driver.page_source.lower()
            if "captcha" in page_src or "blocked" in page_src:
                return SubmissionResult(
                    site="marketing", success=False, error="Bot detection triggered"
                )

            # first name
            for sel in ["input[name='firstName']", "input[name='first_name']",
                        "input[name='fname']", "input[placeholder*='first' i]"]:
                if self._fill_field(By.CSS_SELECTOR, sel, first):
                    break

            await self.random_delay(0.3, 0.8)

            # last name
            for sel in ["input[name='lastName']", "input[name='last_name']",
                        "input[name='lname']", "input[placeholder*='last' i]"]:
                if self._fill_field(By.CSS_SELECTOR, sel, last):
                    break

            await self.random_delay(0.3, 0.8)

            # email
            for sel in ["input[name='email']", "input[type='email']",
                        "input[placeholder*='email' i]"]:
                if self._fill_field(By.CSS_SELECTOR, sel, email):
                    break

            await self.random_delay(0.3, 0.8)

            # address
            for sel in ["input[name='address']", "input[name='address1']",
                        "input[name='street']", "input[placeholder*='address' i]"]:
                if self._fill_field(By.CSS_SELECTOR, sel, street):
                    break

            for sel in ["input[name='city']", "input[placeholder*='city' i]"]:
                if self._fill_field(By.CSS_SELECTOR, sel, city):
                    break

            for sel in ["select[name='state']", "select[name='region']"]:
                if self._select_by_value(By.CSS_SELECTOR, sel, state):
                    break
                if self._select_by_text(By.CSS_SELECTOR, sel, state):
                    break
            else:
                for sel in ["input[name='state']", "input[placeholder*='state' i]"]:
                    if self._fill_field(By.CSS_SELECTOR, sel, state):
                        break

            for sel in ["input[name='zip']", "input[name='zipcode']",
                        "input[name='postalCode']", "input[placeholder*='zip' i]"]:
                if self._fill_field(By.CSS_SELECTOR, sel, zipcode):
                    break

            await self.random_delay(0.3, 0.8)

            # phone
            if phone:
                for sel in ["input[name='phone']", "input[type='tel']",
                            "input[placeholder*='phone' i]"]:
                    if self._fill_field(By.CSS_SELECTOR, sel, phone):
                        break

            # date of birth (some sweepstakes require it)
            if dob:
                for sel in ["input[name='dob']", "input[name='birthdate']",
                            "input[name='date_of_birth']", "input[type='date']"]:
                    if self._fill_field(By.CSS_SELECTOR, sel, dob):
                        break

            await self.random_delay(0.5, 1)

            # agree to terms checkbox (these forms always have one)
            for sel in ["input[name='agree']", "input[name='terms']",
                        "input[name='optin']", "input[type='checkbox']"]:
                if self._click(By.CSS_SELECTOR, sel):
                    break

            await self.random_delay(0.5, 1)

            # submit
            submitted = False
            for sel in ["button[type='submit']", "input[type='submit']",
                        "button[class*='submit']", "button[class*='enter']",
                        "button.btn-primary"]:
                if self._click(By.CSS_SELECTOR, sel):
                    submitted = True
                    break

            if not submitted:
                try:
                    active = self.driver.switch_to.active_element
                    active.send_keys(Keys.RETURN)
                    submitted = True
                except Exception:
                    pass

            if not submitted:
                return SubmissionResult(
                    site="marketing", success=False, error="Could not submit form"
                )

            await self.random_delay(3, 5)

            ref_id = f"mkt-{uuid.uuid4().hex[:8]}"

            return SubmissionResult(
                site="marketing",
                success=True,
                reference_id=ref_id,
                submitted_at=datetime.utcnow(),
                profile_snapshot=profile,
            )

        except Exception as e:
            return SubmissionResult(site="marketing", success=False, error=str(e))


class ManualSubmitter(BaseSubmitter):
    """
    Semi-automated fallback for sites with strict bot detection.
    Generates step-by-step instructions for manual profile creation
    on platforms like LinkedIn, Facebook, Twitter, etc.

    Returns a SubmissionResult with the instructions in profile_snapshot
    so the user can follow them manually. No selenium driver needed.
    """

    # templates for different manual submission targets
    INSTRUCTION_TEMPLATES = {
        "linkedin": {
            "url": "https://www.linkedin.com/signup",
            "steps": [
                "Go to {url}",
                "Create account with email: {email}",
                "Set name to: {first_name} {last_name}",
                "Set location to: {city}, {state}",
                "Set headline to: {job_title} at {company}",
                "Add current position: {job_title} at {company}",
                "Set industry to: {industry}",
                "Make profile public (Settings > Visibility)",
            ],
        },
        "facebook": {
            "url": "https://www.facebook.com/r.php",
            "steps": [
                "Go to {url}",
                "Create account with email: {email}",
                "Set name to: {first_name} {last_name}",
                "Set birthday to: {date_of_birth}",
                "Add current city: {city}, {state}",
                "Add workplace: {company}",
                "Set profile to public",
            ],
        },
        "whitepages_claim": {
            "url": "https://www.whitepages.com/",
            "steps": [
                "Go to {url} and search for: {first_name} {last_name} in {city}, {state}",
                "If a matching record appears, click 'Claim this listing'",
                "Create account with email: {email}",
                "Update the listing with address: {street}, {city}, {state} {zip}",
                "Update phone to: {phone}",
                "Save changes",
            ],
        },
        "generic": {
            "url": "",
            "steps": [
                "Create a public profile on any people-search or social site",
                "Use name: {first_name} {last_name}",
                "Use email: {email}",
                "Use address: {street}, {city}, {state} {zip}",
                "Use phone: {phone}",
                "Set employment to: {job_title} at {company}",
                "Make sure the profile is publicly visible",
            ],
        },
    }

    async def execute(self, profile: dict) -> SubmissionResult:
        """Override execute -- no driver needed for manual instructions."""
        return await self.submit(profile)

    async def submit(self, profile: dict) -> SubmissionResult:
        first = profile.get("first_name", "")
        last = profile.get("last_name", "")
        email = (profile.get("emails") or ["(generate an email)"])[0]
        phones = profile.get("phone_numbers", [])
        phone = phones[0].get("number", "(no phone)") if phones else "(no phone)"
        employment = profile.get("employment", {})
        dob = profile.get("date_of_birth", "")

        street = ""
        city = ""
        state = ""
        zipcode = ""
        if profile.get("addresses"):
            addr = profile["addresses"][0]
            street = addr.get("street", "")
            city = addr.get("city", "")
            state = addr.get("state", "")
            zipcode = addr.get("zip", "")

        # build replacement values
        replacements = {
            "first_name": first,
            "last_name": last,
            "email": email,
            "phone": phone,
            "street": street,
            "city": city,
            "state": state,
            "zip": zipcode,
            "date_of_birth": dob,
            "job_title": employment.get("title", "Professional"),
            "company": employment.get("company", "Self-employed"),
            "industry": employment.get("industry", ""),
        }

        # generate instructions for all templates
        all_instructions = []
        for platform, template in self.INSTRUCTION_TEMPLATES.items():
            url = template["url"]
            replacements["url"] = url
            steps = []
            for i, step in enumerate(template["steps"], 1):
                try:
                    formatted = step.format(**replacements)
                except KeyError:
                    formatted = step
                steps.append(f"  {i}. {formatted}")

            section = f"\n--- {platform.upper()} ---\n" + "\n".join(steps)
            all_instructions.append(section)

        instructions_text = (
            f"Manual submission instructions for: {first} {last}\n"
            + "\n".join(all_instructions)
        )

        ref_id = f"manual-{uuid.uuid4().hex[:8]}"

        return SubmissionResult(
            site="manual",
            success=True,
            reference_id=ref_id,
            submitted_at=datetime.utcnow(),
            profile_snapshot={
                **profile,
                "instructions": instructions_text,
            },
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def random_suffix() -> str:
    """Short random suffix for usernames to avoid collisions."""
    return uuid.uuid4().hex[:5]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

SUBMITTER_REGISTRY: Dict[str, type] = {
    "aboutme": AboutMeSubmitter,
    "gravatar": GravatarSubmitter,
    "linktree": LinktreeSubmitter,
    "directory": DirectorySubmitter,
    "marketing": MarketingFormSubmitter,
    "manual": ManualSubmitter,
}


def get_submitter(site_name: str) -> Optional[BaseSubmitter]:
    """Return an instance of the submitter for the given site, or None."""
    cls = SUBMITTER_REGISTRY.get(site_name.lower())
    return cls() if cls else None
