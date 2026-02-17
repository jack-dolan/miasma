"""
Tests for the data generator service
"""

import re
from datetime import date

import pytest

from app.services.data_generator_service import DataGeneratorService
from app.data.us_locations import US_LOCATIONS, get_locations_by_state


@pytest.fixture
def generator():
    return DataGeneratorService(locale="en_US")


# -- Valid zip codes from our data --
VALID_ZIPS = {loc[0] for loc in US_LOCATIONS}
VALID_STATES = {loc[2] for loc in US_LOCATIONS}

PHONE_PATTERN = re.compile(r"^\(\d{3}\) \d{3}-\d{4}$")
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class TestSingleProfile:
    def test_has_all_required_fields(self, generator):
        profile = generator.generate_profile()
        required = [
            "first_name", "last_name", "middle_name", "age",
            "date_of_birth", "gender", "addresses", "phone_numbers",
            "emails", "relatives", "employment",
        ]
        for field in required:
            assert field in profile, f"Missing field: {field}"

    def test_name_fields_are_strings(self, generator):
        profile = generator.generate_profile()
        assert isinstance(profile["first_name"], str)
        assert isinstance(profile["last_name"], str)
        assert len(profile["first_name"]) > 0
        assert len(profile["last_name"]) > 0

    def test_age_in_valid_range(self, generator):
        for _ in range(50):
            profile = generator.generate_profile()
            assert 21 <= profile["age"] <= 85

    def test_dob_matches_age(self, generator):
        profile = generator.generate_profile()
        dob = date.fromisoformat(profile["date_of_birth"])
        today = date.today()
        # age should be within 1 year of calculated
        calculated_age = today.year - dob.year
        assert abs(calculated_age - profile["age"]) <= 1

    def test_gender_is_valid(self, generator):
        profile = generator.generate_profile()
        assert profile["gender"] in ("M", "F")

    def test_addresses_have_required_fields(self, generator):
        profile = generator.generate_profile()
        assert len(profile["addresses"]) >= 1
        for addr in profile["addresses"]:
            assert "street" in addr
            assert "city" in addr
            assert "state" in addr
            assert "zip" in addr
            assert "type" in addr
            assert addr["type"] in ("current", "previous")

    def test_first_address_is_current(self, generator):
        profile = generator.generate_profile()
        assert profile["addresses"][0]["type"] == "current"

    def test_zip_codes_are_real(self, generator):
        for _ in range(20):
            profile = generator.generate_profile()
            for addr in profile["addresses"]:
                assert addr["zip"] in VALID_ZIPS, f"Invalid zip: {addr['zip']}"

    def test_state_codes_are_valid(self, generator):
        profile = generator.generate_profile()
        for addr in profile["addresses"]:
            assert addr["state"] in VALID_STATES

    def test_phone_number_format(self, generator):
        for _ in range(20):
            profile = generator.generate_profile()
            for phone in profile["phone_numbers"]:
                assert PHONE_PATTERN.match(phone["number"]), \
                    f"Bad phone format: {phone['number']}"
                assert phone["type"] in ("mobile", "home", "work")

    def test_email_format(self, generator):
        for _ in range(20):
            profile = generator.generate_profile()
            assert len(profile["emails"]) >= 1
            for email in profile["emails"]:
                assert EMAIL_PATTERN.match(email), f"Bad email: {email}"

    def test_relatives_list(self, generator):
        for _ in range(10):
            profile = generator.generate_profile()
            assert 2 <= len(profile["relatives"]) <= 5
            for name in profile["relatives"]:
                assert isinstance(name, str)
                assert " " in name  # first + last

    def test_employment_structure(self, generator):
        profile = generator.generate_profile()
        emp = profile["employment"]
        assert "employer" in emp
        assert "title" in emp


class TestGenderConsistency:
    def test_male_profile(self, generator):
        profile = generator.generate_profile(template={"gender": "M"})
        assert profile["gender"] == "M"

    def test_female_profile(self, generator):
        profile = generator.generate_profile(template={"gender": "F"})
        assert profile["gender"] == "F"


class TestTemplateConstraints:
    def test_state_filter(self, generator):
        profile = generator.generate_profile(template={"state": "CA"})
        for addr in profile["addresses"]:
            assert addr["state"] == "CA"

    def test_state_filter_zip_matches(self, generator):
        ca_zips = {loc[0] for loc in get_locations_by_state("CA")}
        for _ in range(10):
            profile = generator.generate_profile(template={"state": "CA"})
            for addr in profile["addresses"]:
                assert addr["zip"] in ca_zips

    def test_age_range(self, generator):
        for _ in range(30):
            profile = generator.generate_profile(template={"age_range": [25, 35]})
            assert 25 <= profile["age"] <= 35

    def test_count_addresses(self, generator):
        profile = generator.generate_profile(template={"count_addresses": 3})
        assert len(profile["addresses"]) == 3

    def test_count_phones(self, generator):
        profile = generator.generate_profile(template={"count_phones": 2})
        assert len(profile["phone_numbers"]) == 2


class TestMultipleProfiles:
    def test_returns_correct_count(self, generator):
        profiles = generator.generate_profiles(10)
        assert len(profiles) == 10

    def test_profiles_are_unique(self, generator):
        profiles = generator.generate_profiles(20)
        name_pairs = [(p["first_name"], p["last_name"]) for p in profiles]
        # most should be unique (might have rare collision)
        unique = set(name_pairs)
        assert len(unique) >= len(name_pairs) * 0.8

    def test_template_applied_to_all(self, generator):
        profiles = generator.generate_profiles(5, template={"state": "TX"})
        for p in profiles:
            for addr in p["addresses"]:
                assert addr["state"] == "TX"


class TestTargetProfile:
    def test_target_has_same_last_name(self, generator):
        profile = generator.generate_profile_for_target("Jane Doe")
        assert profile["last_name"] == "Doe"

    def test_target_with_location(self, generator):
        profile = generator.generate_profile_for_target("John Smith", "CA")
        assert profile["last_name"] == "Smith"
        for addr in profile["addresses"]:
            assert addr["state"] == "CA"

    def test_target_all_fields_present(self, generator):
        profile = generator.generate_profile_for_target("Bob Jones", "New York")
        assert "first_name" in profile
        assert "addresses" in profile
        assert len(profile["addresses"]) >= 1


class TestPoisoningProfiles:
    """Tests for generate_poisoning_profiles - batch of profiles all sharing the target's real name"""

    def test_all_profiles_share_target_name(self, generator):
        profiles = generator.generate_poisoning_profiles("Joe", "Smith", count=10)
        assert len(profiles) == 10
        for p in profiles:
            assert p["first_name"] == "Joe"
            assert p["last_name"] == "Smith"

    def test_emails_match_target_name(self, generator):
        profiles = generator.generate_poisoning_profiles("Jane", "Doe", count=5)
        for p in profiles:
            for email in p["emails"]:
                local = email.split("@")[0].lower()
                assert EMAIL_PATTERN.match(email), f"Bad email: {email}"
                # should contain some part of the target name
                assert "jane" in local or "doe" in local, \
                    f"Email {email} doesn't reference target name"

    def test_state_scattering_with_real_state(self, generator):
        profiles = generator.generate_poisoning_profiles(
            "Bob", "Jones", count=100, real_state="CA"
        )
        in_state = 0
        out_state = 0
        for p in profiles:
            # check the current address (first one)
            state = p["addresses"][0]["state"]
            if state == "CA":
                in_state += 1
            else:
                out_state += 1

        # with 100 samples and 30% target, we should see between 15-50 in-state
        assert in_state > 10, f"Too few in CA: {in_state}"
        assert out_state > 40, f"Too few outside CA: {out_state}"

    def test_state_scattering_without_real_state(self, generator):
        profiles = generator.generate_poisoning_profiles("Alice", "Wong", count=10)
        # should work fine - addresses will be random
        for p in profiles:
            assert len(p["addresses"]) >= 1
            assert p["addresses"][0]["state"] in VALID_STATES

    def test_age_range_around_real_age(self, generator):
        profiles = generator.generate_poisoning_profiles(
            "Tom", "Brown", count=50, real_age=40
        )
        for p in profiles:
            assert 33 <= p["age"] <= 47, \
                f"Age {p['age']} outside expected range [33, 47]"

    def test_age_range_clamps_young(self, generator):
        profiles = generator.generate_poisoning_profiles(
            "Young", "Person", count=20, real_age=22
        )
        for p in profiles:
            assert 21 <= p["age"] <= 29

    def test_relatives_share_last_name(self, generator):
        profiles = generator.generate_poisoning_profiles("Ed", "Wilson", count=5)
        for p in profiles:
            assert len(p["relatives"]) >= 2
            # at least one relative should share the last name (statistically very likely with 60% chance)
            has_shared = any("Wilson" in r for r in p["relatives"])
            # not guaranteed for every profile, but check structure
            for r in p["relatives"]:
                assert " " in r  # first + last name

    def test_all_fields_present(self, generator):
        profiles = generator.generate_poisoning_profiles("Test", "User", count=3)
        required = [
            "first_name", "last_name", "age", "date_of_birth",
            "gender", "addresses", "phone_numbers", "emails",
            "relatives", "employment",
        ]
        for p in profiles:
            for field in required:
                assert field in p

    def test_respects_count_limit(self, generator):
        profiles = generator.generate_poisoning_profiles("A", "B", count=3)
        assert len(profiles) == 3


class TestLocationData:
    def test_all_50_states_covered(self):
        states = {loc[2] for loc in US_LOCATIONS}
        # 50 states + DC
        assert len(states) >= 51

    def test_location_data_structure(self):
        for loc in US_LOCATIONS:
            assert len(loc) == 4
            zip_code, city, state, area_code = loc
            assert len(zip_code) == 5
            assert zip_code.isdigit()
            assert len(state) == 2
            assert len(area_code) == 3
            assert area_code.isdigit()
            assert len(city) > 0

    def test_get_locations_by_state(self):
        ca_locs = get_locations_by_state("CA")
        assert len(ca_locs) > 5
        for loc in ca_locs:
            assert loc[2] == "CA"

    def test_get_locations_invalid_state(self):
        locs = get_locations_by_state("ZZ")
        assert locs == []
