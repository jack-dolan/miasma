"""
Fake profile generation for data poisoning campaigns.
Generates realistic-looking US person profiles using Faker + real zip/area code data.
"""

import random
import string
from datetime import date, timedelta
from typing import Optional

from faker import Faker

from app.data.us_locations import US_LOCATIONS, get_locations_by_state, ALL_STATES


# Common email providers weighted by popularity
EMAIL_DOMAINS = [
    ("gmail.com", 0.45),
    ("yahoo.com", 0.18),
    ("outlook.com", 0.12),
    ("hotmail.com", 0.08),
    ("aol.com", 0.05),
    ("icloud.com", 0.05),
    ("mail.com", 0.03),
    ("protonmail.com", 0.02),
    ("comcast.net", 0.02),
]

# Street types for more variety
STREET_SUFFIXES = [
    "St", "Ave", "Blvd", "Dr", "Ln", "Ct", "Pl", "Way", "Rd", "Cir", "Ter",
]

# Weighted domains helper
_DOMAIN_NAMES = [d[0] for d in EMAIL_DOMAINS]
_DOMAIN_WEIGHTS = [d[1] for d in EMAIL_DOMAINS]


def _pick_email_domain() -> str:
    return random.choices(_DOMAIN_NAMES, weights=_DOMAIN_WEIGHTS, k=1)[0]


def _weighted_age() -> int:
    """Pick an age between 21-85, weighted toward 30-60."""
    # use a triangular distribution centered around 42
    age = int(random.triangular(21, 85, 42))
    return max(21, min(85, age))


def _dob_from_age(age: int) -> date:
    """Calculate a plausible date of birth from age."""
    today = date.today()
    # random day in the year they'd turn this age
    year = today.year - age
    month = random.randint(1, 12)
    max_day = 28  # safe for all months
    if month in (1, 3, 5, 7, 8, 10, 12):
        max_day = 31
    elif month in (4, 6, 9, 11):
        max_day = 30
    day = random.randint(1, max_day)
    return date(year, month, day)


class DataGeneratorService:

    def __init__(self, locale: str = "en_US"):
        self.fake = Faker(locale)

    def _pick_location(self, state: str | None = None) -> tuple:
        """Pick a random real US location, optionally in a specific state."""
        if state:
            locs = get_locations_by_state(state)
            if locs:
                return random.choice(locs)
        return random.choice(US_LOCATIONS)

    def _generate_street(self) -> str:
        """Generate a realistic street address."""
        num = random.randint(100, 19999)
        # mix of faker street names and our own patterns
        if random.random() < 0.5:
            name = self.fake.street_name()
        else:
            name = f"{self.fake.first_name()} {random.choice(STREET_SUFFIXES)}"
        return f"{num} {name}"

    def _generate_phone(self, area_code: str) -> str:
        """Generate a phone number with the given area code."""
        exchange = random.randint(200, 999)
        subscriber = random.randint(1000, 9999)
        return f"({area_code}) {exchange}-{subscriber}"

    def _generate_emails(self, first: str, last: str, middle: str | None = None) -> list[str]:
        """Generate 1-3 realistic email addresses from a person's name."""
        first_l = first.lower()
        last_l = last.lower()
        mid_init = middle[0].lower() if middle else ""

        patterns = [
            f"{first_l}.{last_l}",
            f"{first_l[0]}{last_l}",
            f"{first_l}{last_l[0]}",
            f"{first_l}_{last_l}",
            f"{first_l}{last_l}",
            f"{last_l}.{first_l}",
            f"{first_l}.{mid_init}.{last_l}" if mid_init else f"{first_l}{last_l}",
            f"{first_l}{random.randint(1, 99)}",
            f"{first_l}.{last_l}{random.randint(1, 999)}",
        ]

        count = random.choices([1, 2, 3], weights=[0.3, 0.5, 0.2], k=1)[0]
        chosen = random.sample(patterns, min(count, len(patterns)))

        emails = []
        for local in chosen:
            # clean up any weird chars
            local = "".join(c for c in local if c.isalnum() or c in "._-")
            domain = _pick_email_domain()
            emails.append(f"{local}@{domain}")

        return emails

    def _generate_relatives(self, last_name: str) -> list[str]:
        """Generate 2-5 relative names, some sharing the last name."""
        count = random.randint(2, 5)
        relatives = []
        for _ in range(count):
            if random.random() < 0.6:
                # same last name (sibling, parent, child)
                rel_last = last_name
            else:
                # different last name (in-law, married sibling)
                rel_last = self.fake.last_name()
            gender = random.choice(["M", "F"])
            if gender == "M":
                rel_first = self.fake.first_name_male()
            else:
                rel_first = self.fake.first_name_female()
            relatives.append(f"{rel_first} {rel_last}")
        return relatives

    def generate_profile(self, template: dict | None = None) -> dict:
        """Generate a single fake person profile.

        Template keys:
            state: 2-letter state code to constrain addresses
            age_range: [min_age, max_age] tuple
            count_addresses: number of addresses (1-4)
            count_phones: number of phone numbers (1-3)
            gender: "M" or "F" to force gender
        """
        template = template or {}

        # Gender
        gender = template.get("gender")
        if gender not in ("M", "F"):
            gender = random.choice(["M", "F"])

        # Name generation
        if gender == "M":
            first_name = self.fake.first_name_male()
            middle_name = self.fake.first_name_male() if random.random() < 0.7 else None
        else:
            first_name = self.fake.first_name_female()
            middle_name = self.fake.first_name_female() if random.random() < 0.7 else None

        last_name = self.fake.last_name()

        # Age
        age_range = template.get("age_range")
        if age_range and len(age_range) == 2:
            lo, hi = int(age_range[0]), int(age_range[1])
            age = int(random.triangular(lo, hi, (lo + hi) / 2))
            age = max(lo, min(hi, age))
        else:
            age = _weighted_age()

        dob = _dob_from_age(age)

        # Addresses
        state_filter = template.get("state")
        num_addresses = template.get("count_addresses") or random.choices([1, 2, 3], weights=[0.3, 0.5, 0.2], k=1)[0]
        num_addresses = max(1, min(4, int(num_addresses)))

        addresses = []
        used_zips = set()
        for i in range(num_addresses):
            loc = self._pick_location(state_filter)
            zip_code, city, state, area_code = loc

            # try not to duplicate zips
            attempts = 0
            while zip_code in used_zips and attempts < 10:
                loc = self._pick_location(state_filter)
                zip_code, city, state, area_code = loc
                attempts += 1
            used_zips.add(zip_code)

            addr_type = "current" if i == 0 else "previous"
            addresses.append({
                "street": self._generate_street(),
                "city": city,
                "state": state,
                "zip": zip_code,
                "type": addr_type,
            })

        # Phone numbers - area codes match address states
        num_phones = template.get("count_phones") or random.choices([1, 2, 3], weights=[0.3, 0.5, 0.2], k=1)[0]
        num_phones = max(1, min(3, int(num_phones)))

        phone_types = ["mobile", "home", "work"]
        phones = []
        for i in range(num_phones):
            # use area code from one of the addresses
            addr = addresses[i % len(addresses)]
            loc = self._pick_location(addr["state"])
            area_code = loc[3]
            ptype = phone_types[i] if i < len(phone_types) else "mobile"
            phones.append({
                "number": self._generate_phone(area_code),
                "type": ptype,
            })

        # Emails
        emails = self._generate_emails(first_name, last_name, middle_name)

        # Relatives
        relatives = self._generate_relatives(last_name)

        # Employment (optional)
        has_job = random.random() < 0.75
        employment = {
            "employer": self.fake.company() if has_job else None,
            "title": self.fake.job() if has_job else None,
        }

        return {
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": middle_name,
            "age": age,
            "date_of_birth": dob.isoformat(),
            "gender": gender,
            "addresses": addresses,
            "phone_numbers": phones,
            "emails": emails,
            "relatives": relatives,
            "employment": employment,
        }

    def generate_profiles(self, count: int, template: dict | None = None) -> list[dict]:
        """Generate multiple unique profiles."""
        profiles = []
        seen_names = set()

        # cap at something reasonable
        count = min(count, 500)

        for _ in range(count):
            # retry a few times to avoid duplicate names
            for attempt in range(5):
                profile = self.generate_profile(template)
                name_key = (profile["first_name"], profile["last_name"])
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    profiles.append(profile)
                    break
            else:
                # if we can't get unique after retries, add it anyway
                profiles.append(profile)

        return profiles

    def generate_poisoning_profiles(
        self,
        first_name: str,
        last_name: str,
        count: int = 10,
        real_state: str | None = None,
        real_age: int | None = None,
    ) -> list[dict]:
        """Generate N fake profiles all sharing the target's real name.
        Each has different fake addresses, phones, emails, etc.
        About 30% of profiles use the same state as the real person (if provided),
        70% are scattered across other states."""

        count = min(count, 500)

        # build per-profile templates
        profiles = []
        for i in range(count):
            template = {}

            if real_state:
                # ~30% in the real state, rest scattered
                if random.random() < 0.3:
                    template["state"] = real_state
                else:
                    # pick a different state
                    other_states = [s for s in ALL_STATES if s != real_state]
                    template["state"] = random.choice(other_states)

            if real_age:
                lo = max(21, real_age - 7)
                hi = min(85, real_age + 7)
                template["age_range"] = [lo, hi]

            profile = self.generate_profile(template)

            # override name with the real target's name
            profile["first_name"] = first_name
            profile["last_name"] = last_name

            # regenerate emails to match the real name
            profile["emails"] = self._generate_emails(
                first_name, last_name, profile.get("middle_name")
            )

            # regenerate relatives so some share the target's last name
            profile["relatives"] = self._generate_relatives(last_name)

            profiles.append(profile)

        return profiles

    def generate_profile_for_target(
        self, target_name: str, target_location: str | None = None
    ) -> dict:
        """Generate a profile that's plausibly similar to a real target.

        Uses the same geographic area and a similar-sounding name variant.
        This creates noise that's hard to distinguish from real records.
        """
        parts = target_name.strip().split()
        target_first = parts[0] if parts else "John"
        target_last = parts[-1] if len(parts) > 1 else "Smith"

        # Parse location into state if possible
        state = None
        if target_location:
            loc_upper = target_location.strip().upper()
            # check if it's a state code
            if len(loc_upper) == 2 and loc_upper in ALL_STATES:
                state = loc_upper
            else:
                # try to find state from location data
                for entry in US_LOCATIONS:
                    if loc_upper in entry[1].upper() or loc_upper == entry[2]:
                        state = entry[2]
                        break

        template = {}
        if state:
            template["state"] = state

        # generate a profile in the same area
        profile = self.generate_profile(template)

        # give it the same last name to create confusion with real records
        profile["last_name"] = target_last

        return profile
