"""
Tests for the submission engine upstream source submitters
"""

from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock

import pytest

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


# -- fixtures --

@pytest.fixture
def sample_profile():
    """Full profile matching the expected input format"""
    return {
        "first_name": "Joe",
        "last_name": "Smith",
        "date_of_birth": "1991-03-15",
        "age": 32,
        "addresses": [{"street": "742 Elm St", "city": "Denver", "state": "CO", "zip": "80202"}],
        "phone_numbers": [{"number": "555-867-5309", "type": "mobile"}],
        "emails": ["joe.fake@example.com"],
        "relatives": [{"first_name": "Jane", "last_name": "Smith", "relationship": "spouse"}],
        "employment": {"company": "Acme Corp", "title": "Sales Manager", "industry": "Retail"},
    }


@pytest.fixture
def minimal_profile():
    """Bare-minimum profile with just name"""
    return {
        "first_name": "Jane",
        "last_name": "Doe",
    }


@pytest.fixture
def mock_driver():
    """Selenium driver mock with common attributes"""
    driver = MagicMock()
    driver.page_source = "<html><body>normal page</body></html>"
    driver.find_element.return_value = MagicMock()
    driver.switch_to.active_element = MagicMock()
    return driver


# -- SubmissionResult tests --

class TestSubmissionResult:

    def test_create_success(self):
        result = SubmissionResult(site="test", success=True, reference_id="ref-123")
        assert result.site == "test"
        assert result.success is True
        assert result.reference_id == "ref-123"
        assert result.error is None

    def test_create_failure(self):
        result = SubmissionResult(site="test", success=False, error="something broke")
        assert result.success is False
        assert result.error == "something broke"

    def test_defaults(self):
        result = SubmissionResult(site="x", success=True)
        assert result.reference_id is None
        assert result.submitted_at is None
        assert result.profile_snapshot == {}

    def test_with_snapshot(self, sample_profile):
        result = SubmissionResult(
            site="aboutme", success=True,
            submitted_at=datetime.utcnow(),
            profile_snapshot=sample_profile,
        )
        assert result.profile_snapshot["first_name"] == "Joe"


# -- Registry tests --

class TestRegistry:

    def test_all_keys_present(self):
        expected = {"aboutme", "gravatar", "linktree", "directory", "marketing", "manual"}
        assert set(SUBMITTER_REGISTRY.keys()) == expected

    def test_get_submitter_returns_instance(self):
        for key in SUBMITTER_REGISTRY:
            submitter = get_submitter(key)
            assert submitter is not None
            assert isinstance(submitter, BaseSubmitter)

    def test_get_submitter_case_insensitive(self):
        assert get_submitter("AboutMe") is not None
        assert get_submitter("GRAVATAR") is not None

    def test_get_submitter_unknown_returns_none(self):
        assert get_submitter("nonexistent") is None
        assert get_submitter("") is None

    def test_submitter_site_names(self):
        assert get_submitter("aboutme").site_name == "aboutme"
        assert get_submitter("gravatar").site_name == "gravatar"
        assert get_submitter("linktree").site_name == "linktree"
        assert get_submitter("directory").site_name == "directory"
        assert get_submitter("marketing").site_name == "marketingform"
        assert get_submitter("manual").site_name == "manual"


# -- AboutMeSubmitter tests --

class TestAboutMeSubmitter:

    @pytest.mark.asyncio
    async def test_requires_email(self, minimal_profile):
        sub = AboutMeSubmitter()
        sub.initialize_driver = AsyncMock(return_value=True)
        sub.close_driver = AsyncMock()
        result = await sub.execute(minimal_profile)
        assert result.success is False
        assert "Email required" in result.error

    @pytest.mark.asyncio
    async def test_driver_init_failure(self, sample_profile):
        sub = AboutMeSubmitter()
        sub.initialize_driver = AsyncMock(return_value=False)
        sub.close_driver = AsyncMock()
        result = await sub.execute(sample_profile)
        assert result.success is False
        assert "Driver init failed" in result.error

    @pytest.mark.asyncio
    async def test_submit_success(self, sample_profile, mock_driver):
        sub = AboutMeSubmitter()
        sub.driver = mock_driver
        sub.safe_get = AsyncMock(return_value=True)
        sub.random_delay = AsyncMock()
        sub._fill_field = MagicMock(return_value=True)
        sub._click = MagicMock(return_value=True)

        result = await sub.submit(sample_profile)
        assert result.success is True
        assert result.site == "aboutme"
        assert result.reference_id.startswith("am-")
        assert result.submitted_at is not None
        assert result.profile_snapshot == sample_profile

    @pytest.mark.asyncio
    async def test_bot_detection(self, sample_profile, mock_driver):
        sub = AboutMeSubmitter()
        mock_driver.page_source = "<html>captcha detected</html>"
        sub.driver = mock_driver
        sub.safe_get = AsyncMock(return_value=True)
        sub.random_delay = AsyncMock()

        result = await sub.submit(sample_profile)
        assert result.success is False
        assert "Bot detection" in result.error

    @pytest.mark.asyncio
    async def test_page_load_failure(self, sample_profile, mock_driver):
        sub = AboutMeSubmitter()
        sub.driver = mock_driver
        sub.safe_get = AsyncMock(return_value=False)
        sub.random_delay = AsyncMock()

        result = await sub.submit(sample_profile)
        assert result.success is False
        assert "Failed to load" in result.error


# -- GravatarSubmitter tests --

class TestGravatarSubmitter:

    @pytest.mark.asyncio
    async def test_requires_email(self, minimal_profile):
        sub = GravatarSubmitter()
        sub.initialize_driver = AsyncMock(return_value=True)
        sub.close_driver = AsyncMock()
        result = await sub.execute(minimal_profile)
        assert result.success is False
        assert "Email required" in result.error

    @pytest.mark.asyncio
    async def test_submit_success(self, sample_profile, mock_driver):
        sub = GravatarSubmitter()
        sub.driver = mock_driver
        sub.safe_get = AsyncMock(return_value=True)
        sub.random_delay = AsyncMock()
        sub._fill_field = MagicMock(return_value=True)
        sub._click = MagicMock(return_value=True)

        result = await sub.submit(sample_profile)
        assert result.success is True
        assert result.site == "gravatar"
        assert result.reference_id.startswith("gv-")

    @pytest.mark.asyncio
    async def test_page_load_failure(self, sample_profile, mock_driver):
        sub = GravatarSubmitter()
        sub.driver = mock_driver
        sub.safe_get = AsyncMock(return_value=False)
        sub.random_delay = AsyncMock()

        result = await sub.submit(sample_profile)
        assert result.success is False


# -- LinktreeSubmitter tests --

class TestLinktreeSubmitter:

    @pytest.mark.asyncio
    async def test_requires_email(self, minimal_profile):
        sub = LinktreeSubmitter()
        sub.initialize_driver = AsyncMock(return_value=True)
        sub.close_driver = AsyncMock()
        result = await sub.execute(minimal_profile)
        assert result.success is False
        assert "Email required" in result.error

    @pytest.mark.asyncio
    async def test_submit_success(self, sample_profile, mock_driver):
        sub = LinktreeSubmitter()
        sub.driver = mock_driver
        sub.safe_get = AsyncMock(return_value=True)
        sub.random_delay = AsyncMock()
        sub._fill_field = MagicMock(return_value=True)
        sub._click = MagicMock(return_value=True)

        result = await sub.submit(sample_profile)
        assert result.success is True
        assert result.site == "linktree"
        assert result.reference_id.startswith("lt-")

    @pytest.mark.asyncio
    async def test_bot_detection(self, sample_profile, mock_driver):
        sub = LinktreeSubmitter()
        mock_driver.page_source = "<html>challenge required</html>"
        sub.driver = mock_driver
        sub.safe_get = AsyncMock(return_value=True)
        sub.random_delay = AsyncMock()

        result = await sub.submit(sample_profile)
        assert result.success is False
        assert "Bot detection" in result.error


# -- DirectorySubmitter tests --

class TestDirectorySubmitter:

    @pytest.mark.asyncio
    async def test_requires_email(self, minimal_profile):
        sub = DirectorySubmitter()
        sub.initialize_driver = AsyncMock(return_value=True)
        sub.close_driver = AsyncMock()
        result = await sub.execute(minimal_profile)
        assert result.success is False
        assert "Email required" in result.error

    @pytest.mark.asyncio
    async def test_submit_success(self, sample_profile, mock_driver):
        sub = DirectorySubmitter()
        sub.driver = mock_driver
        sub.safe_get = AsyncMock(return_value=True)
        sub.random_delay = AsyncMock()
        sub._fill_field = MagicMock(return_value=True)
        sub._click = MagicMock(return_value=True)
        sub._select_by_value = MagicMock(return_value=False)
        sub._select_by_text = MagicMock(return_value=False)

        result = await sub.submit(sample_profile)
        assert result.success is True
        assert result.site == "directory"
        assert result.reference_id.startswith("dir-")

    @pytest.mark.asyncio
    async def test_all_directories_fail(self, sample_profile, mock_driver):
        sub = DirectorySubmitter()
        sub.driver = mock_driver
        sub.safe_get = AsyncMock(return_value=False)
        sub.random_delay = AsyncMock()

        result = await sub.submit(sample_profile)
        assert result.success is False
        assert "Could not load" in result.error

    @pytest.mark.asyncio
    async def test_uses_company_name(self, sample_profile, mock_driver):
        sub = DirectorySubmitter()
        sub.driver = mock_driver
        sub.safe_get = AsyncMock(return_value=True)
        sub.random_delay = AsyncMock()
        sub._fill_field = MagicMock(return_value=True)
        sub._click = MagicMock(return_value=True)
        sub._select_by_value = MagicMock(return_value=False)
        sub._select_by_text = MagicMock(return_value=False)

        await sub.submit(sample_profile)

        # check that _fill_field was called with the company name somewhere
        calls = [str(c) for c in sub._fill_field.call_args_list]
        found_company = any("Acme Corp" in c for c in calls)
        assert found_company


# -- MarketingFormSubmitter tests --

class TestMarketingFormSubmitter:

    @pytest.mark.asyncio
    async def test_requires_email(self, minimal_profile):
        sub = MarketingFormSubmitter()
        sub.initialize_driver = AsyncMock(return_value=True)
        sub.close_driver = AsyncMock()
        result = await sub.execute(minimal_profile)
        assert result.success is False
        assert "Email required" in result.error

    @pytest.mark.asyncio
    async def test_submit_success(self, sample_profile, mock_driver):
        sub = MarketingFormSubmitter()
        sub.driver = mock_driver
        sub.safe_get = AsyncMock(return_value=True)
        sub.random_delay = AsyncMock()
        sub._fill_field = MagicMock(return_value=True)
        sub._click = MagicMock(return_value=True)
        sub._select_by_value = MagicMock(return_value=False)
        sub._select_by_text = MagicMock(return_value=False)

        result = await sub.submit(sample_profile)
        assert result.success is True
        assert result.site == "marketing"
        assert result.reference_id.startswith("mkt-")

    @pytest.mark.asyncio
    async def test_all_forms_fail(self, sample_profile, mock_driver):
        sub = MarketingFormSubmitter()
        sub.driver = mock_driver
        sub.safe_get = AsyncMock(return_value=False)
        sub.random_delay = AsyncMock()

        result = await sub.submit(sample_profile)
        assert result.success is False
        assert "Could not load" in result.error


# -- ManualSubmitter tests --

class TestManualSubmitter:

    @pytest.mark.asyncio
    async def test_returns_instructions(self, sample_profile):
        sub = ManualSubmitter()
        result = await sub.execute(sample_profile)
        assert result.success is True
        assert result.site == "manual"
        assert result.reference_id.startswith("manual-")
        assert "instructions" in result.profile_snapshot

    @pytest.mark.asyncio
    async def test_instructions_contain_name(self, sample_profile):
        sub = ManualSubmitter()
        result = await sub.execute(sample_profile)
        instructions = result.profile_snapshot["instructions"]
        assert "Joe" in instructions
        assert "Smith" in instructions

    @pytest.mark.asyncio
    async def test_instructions_contain_platforms(self, sample_profile):
        sub = ManualSubmitter()
        result = await sub.execute(sample_profile)
        instructions = result.profile_snapshot["instructions"]
        assert "LINKEDIN" in instructions
        assert "FACEBOOK" in instructions
        assert "WHITEPAGES_CLAIM" in instructions
        assert "GENERIC" in instructions

    @pytest.mark.asyncio
    async def test_instructions_contain_profile_data(self, sample_profile):
        sub = ManualSubmitter()
        result = await sub.execute(sample_profile)
        instructions = result.profile_snapshot["instructions"]
        assert "joe.fake@example.com" in instructions
        assert "Denver" in instructions
        assert "Acme Corp" in instructions

    @pytest.mark.asyncio
    async def test_no_driver_needed(self, sample_profile):
        """ManualSubmitter.execute() should work without calling initialize_driver"""
        sub = ManualSubmitter()
        # don't mock any driver stuff -- it shouldn't touch the driver at all
        result = await sub.execute(sample_profile)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_minimal_profile_still_works(self, minimal_profile):
        sub = ManualSubmitter()
        result = await sub.execute(minimal_profile)
        assert result.success is True
        assert "Jane" in result.profile_snapshot["instructions"]
        assert "Doe" in result.profile_snapshot["instructions"]

    @pytest.mark.asyncio
    async def test_preserves_original_profile(self, sample_profile):
        sub = ManualSubmitter()
        result = await sub.execute(sample_profile)
        # original profile fields should still be in the snapshot
        assert result.profile_snapshot["first_name"] == "Joe"
        assert result.profile_snapshot["last_name"] == "Smith"
        assert result.profile_snapshot["emails"] == ["joe.fake@example.com"]


# -- BaseSubmitter execute() tests --

class TestBaseSubmitterExecute:

    @pytest.mark.asyncio
    async def test_execute_calls_close_on_success(self, sample_profile, mock_driver):
        sub = AboutMeSubmitter()
        sub.initialize_driver = AsyncMock(return_value=True)
        sub.close_driver = AsyncMock()
        sub.driver = mock_driver
        sub.safe_get = AsyncMock(return_value=True)
        sub.random_delay = AsyncMock()
        sub._fill_field = MagicMock(return_value=True)
        sub._click = MagicMock(return_value=True)

        await sub.execute(sample_profile)
        sub.close_driver.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_calls_close_on_failure(self, sample_profile):
        sub = AboutMeSubmitter()
        sub.initialize_driver = AsyncMock(return_value=True)
        sub.close_driver = AsyncMock()
        sub.submit = AsyncMock(side_effect=RuntimeError("boom"))

        await sub.execute(sample_profile)
        sub.close_driver.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_returns_error_on_driver_fail(self, sample_profile):
        sub = AboutMeSubmitter()
        sub.initialize_driver = AsyncMock(return_value=False)
        sub.close_driver = AsyncMock()

        result = await sub.execute(sample_profile)
        assert result.success is False
        assert "Driver init" in result.error
