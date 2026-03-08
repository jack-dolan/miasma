"""
Unit tests for FastPeopleSearch opt-out handler helper logic.
"""

from app.services.optout_handlers.fastpeoplesearch import FastPeopleSearchOptoutHandler


def test_build_search_url_with_city_state():
    handler = FastPeopleSearchOptoutHandler()
    url = handler._build_search_url("Jane", "Doe", city="San Diego", state="CA")
    assert url == "https://www.fastpeoplesearch.com/name/jane-doe_san-diego-ca"


def test_build_search_url_with_state_only():
    handler = FastPeopleSearchOptoutHandler()
    url = handler._build_search_url("Jane", "Doe", state="CA")
    assert url == "https://www.fastpeoplesearch.com/name/jane-doe_ca"


def test_candidate_score_prefers_better_match():
    handler = FastPeopleSearchOptoutHandler()
    strong = handler._candidate_score(
        text="Jane Doe, San Diego CA, Age 36",
        first_name="Jane",
        last_name="Doe",
        city="San Diego",
        state="CA",
        age=36,
    )
    weak = handler._candidate_score(
        text="John Smith, Miami FL",
        first_name="Jane",
        last_name="Doe",
        city="San Diego",
        state="CA",
        age=36,
    )
    assert strong > weak
    assert strong >= 9


def test_extract_location_from_profile():
    handler = FastPeopleSearchOptoutHandler()
    profile = {"addresses": [{"city": "Austin", "state": "TX"}]}
    city, state = handler._extract_location(profile)
    assert city == "Austin"
    assert state == "TX"
