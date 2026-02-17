"""
Tests for the submission engine -- result dataclass, base submitter workflow,
registry, and site-specific submitter metadata.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.submission_engine import (
    SubmissionResult,
    BaseSubmitter,
    AboutMeSubmitter,
    GravatarSubmitter,
    LinktreeSubmitter,
    DirectorySubmitter,
    MarketingFormSubmitter,
    ManualSubmitter,
    SUBMITTER_REGISTRY,
    get_submitter,
)


# ---------------------------------------------------------------------------
# SubmissionResult dataclass
# ---------------------------------------------------------------------------

class TestSubmissionResult:

    def test_create_success(self):
        r = SubmissionResult(
            site="aboutme",
            success=True,
            reference_id="ABC-123",
            submitted_at=datetime(2026, 2, 8, 12, 0),
            profile_snapshot={"first_name": "Jane"},
        )
        assert r.site == "aboutme"
        assert r.success is True
        assert r.reference_id == "ABC-123"
        assert r.error is None
        assert r.profile_snapshot == {"first_name": "Jane"}

    def test_create_failure(self):
        r = SubmissionResult(site="gravatar", success=False, error="CAPTCHA detected")
        assert r.success is False
        assert r.error == "CAPTCHA detected"
        assert r.reference_id is None
        assert r.submitted_at is None

    def test_defaults(self):
        r = SubmissionResult(site="x", success=True)
        assert r.reference_id is None
        assert r.error is None
        assert r.submitted_at is None
        assert r.profile_snapshot == {}


# ---------------------------------------------------------------------------
# BaseSubmitter.execute() workflow
# ---------------------------------------------------------------------------

class TestBaseSubmitterExecute:

    @pytest.mark.asyncio
    async def test_execute_driver_init_failure(self):
        """If the driver fails to init, execute returns failure."""
        sub = AboutMeSubmitter()
        with patch.object(sub, "initialize_driver", new_callable=AsyncMock, return_value=False):
            with patch.object(sub, "close_driver", new_callable=AsyncMock):
                result = await sub.execute({"first_name": "Test", "last_name": "User", "emails": ["t@t.com"]})
        assert result.success is False
        assert "Driver init failed" in result.error

    @pytest.mark.asyncio
    async def test_execute_calls_submit_on_success(self):
        """When driver init succeeds, execute should call submit and return its result."""
        sub = AboutMeSubmitter()
        expected = SubmissionResult(site="aboutme", success=True, reference_id="ref-1")

        with patch.object(sub, "initialize_driver", new_callable=AsyncMock, return_value=True):
            with patch.object(sub, "submit", new_callable=AsyncMock, return_value=expected):
                with patch.object(sub, "close_driver", new_callable=AsyncMock):
                    result = await sub.execute({"first_name": "Test", "last_name": "User"})

        assert result.success is True
        assert result.reference_id == "ref-1"

    @pytest.mark.asyncio
    async def test_execute_catches_exception(self):
        """Exceptions during submit should be caught and returned as failures."""
        sub = GravatarSubmitter()

        with patch.object(sub, "initialize_driver", new_callable=AsyncMock, return_value=True):
            with patch.object(sub, "submit", new_callable=AsyncMock,
                              side_effect=RuntimeError("browser crashed")):
                with patch.object(sub, "close_driver", new_callable=AsyncMock):
                    result = await sub.execute({"first_name": "X", "last_name": "Y"})

        assert result.success is False
        assert "browser crashed" in result.error

    @pytest.mark.asyncio
    async def test_execute_always_closes_driver(self):
        """close_driver must be called even if submit throws."""
        sub = LinktreeSubmitter()
        close_mock = AsyncMock()

        with patch.object(sub, "initialize_driver", new_callable=AsyncMock, return_value=True):
            with patch.object(sub, "submit", new_callable=AsyncMock,
                              side_effect=Exception("boom")):
                with patch.object(sub, "close_driver", close_mock):
                    await sub.execute({})

        close_mock.assert_awaited_once()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestSubmitterRegistry:

    def test_registry_has_aboutme(self):
        assert "aboutme" in SUBMITTER_REGISTRY
        assert SUBMITTER_REGISTRY["aboutme"] is AboutMeSubmitter

    def test_registry_has_gravatar(self):
        assert "gravatar" in SUBMITTER_REGISTRY
        assert SUBMITTER_REGISTRY["gravatar"] is GravatarSubmitter

    def test_registry_has_linktree(self):
        assert "linktree" in SUBMITTER_REGISTRY
        assert SUBMITTER_REGISTRY["linktree"] is LinktreeSubmitter

    def test_registry_has_directory(self):
        assert "directory" in SUBMITTER_REGISTRY
        assert SUBMITTER_REGISTRY["directory"] is DirectorySubmitter

    def test_registry_has_marketing(self):
        assert "marketing" in SUBMITTER_REGISTRY
        assert SUBMITTER_REGISTRY["marketing"] is MarketingFormSubmitter

    def test_registry_has_manual(self):
        assert "manual" in SUBMITTER_REGISTRY
        assert SUBMITTER_REGISTRY["manual"] is ManualSubmitter

    def test_get_submitter_known(self):
        sub = get_submitter("aboutme")
        assert isinstance(sub, AboutMeSubmitter)

    def test_get_submitter_case_insensitive(self):
        sub = get_submitter("AboutMe")
        assert isinstance(sub, AboutMeSubmitter)

    def test_get_submitter_unknown_returns_none(self):
        assert get_submitter("nonexistent_site") is None

    def test_get_submitter_empty_string(self):
        assert get_submitter("") is None


# ---------------------------------------------------------------------------
# Site-specific submitter metadata
# ---------------------------------------------------------------------------

class TestAboutMeSubmitter:

    def test_site_name(self):
        sub = AboutMeSubmitter()
        assert sub.site_name == "aboutme"

    def test_signup_url(self):
        assert "about.me" in AboutMeSubmitter.SIGNUP_URL

    def test_is_base_submitter(self):
        assert issubclass(AboutMeSubmitter, BaseSubmitter)


class TestGravatarSubmitter:

    def test_site_name(self):
        sub = GravatarSubmitter()
        assert sub.site_name == "gravatar"

    def test_signup_url(self):
        assert "gravatar.com" in GravatarSubmitter.SIGNUP_URL

    def test_is_base_submitter(self):
        assert issubclass(GravatarSubmitter, BaseSubmitter)


class TestDirectorySubmitter:

    def test_site_name(self):
        sub = DirectorySubmitter()
        assert sub.site_name == "directory"

    def test_has_directory_urls(self):
        assert len(DirectorySubmitter.DIRECTORY_URLS) > 0

    def test_is_base_submitter(self):
        assert issubclass(DirectorySubmitter, BaseSubmitter)


class TestManualSubmitter:

    def test_site_name(self):
        sub = ManualSubmitter()
        assert sub.site_name == "manual"

    def test_has_instruction_templates(self):
        assert len(ManualSubmitter.INSTRUCTION_TEMPLATES) > 0

    def test_is_base_submitter(self):
        assert issubclass(ManualSubmitter, BaseSubmitter)


# ---------------------------------------------------------------------------
# Helper methods
# ---------------------------------------------------------------------------

class TestHelperMethods:

    def test_fill_field_no_driver(self):
        """_fill_field should return False when element not found."""
        sub = AboutMeSubmitter()
        sub.driver = MagicMock()
        sub.driver.find_element.side_effect = Exception("nope")
        with patch.object(sub, "find_element_safe", return_value=None):
            assert sub._fill_field("css", "input#foo", "text") is False

    def test_fill_field_success(self):
        sub = AboutMeSubmitter()
        mock_el = MagicMock()
        with patch.object(sub, "find_element_safe", return_value=mock_el):
            assert sub._fill_field("css", "input#foo", "hello") is True
        mock_el.clear.assert_called_once()
        mock_el.send_keys.assert_called_once_with("hello")

    def test_click_not_found(self):
        sub = GravatarSubmitter()
        with patch.object(sub, "find_element_safe", return_value=None):
            assert sub._click("css", "button.go") is False

    def test_click_success(self):
        sub = GravatarSubmitter()
        mock_el = MagicMock()
        with patch.object(sub, "find_element_safe", return_value=mock_el):
            assert sub._click("css", "button.go") is True
        mock_el.click.assert_called_once()

    def test_select_by_text_not_found(self):
        sub = DirectorySubmitter()
        with patch.object(sub, "find_element_safe", return_value=None):
            assert sub._select_by_text("css", "select#state", "CA") is False

    def test_select_by_value_not_found(self):
        sub = DirectorySubmitter()
        with patch.object(sub, "find_element_safe", return_value=None):
            assert sub._select_by_value("css", "select#state", "CA") is False
