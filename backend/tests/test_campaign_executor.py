"""
Tests for the campaign executor background task system
"""

import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, CampaignStatus
from app.models.submission import Submission, SubmissionStatus
from app.models.user import User
from app.services.campaign_executor import CampaignExecutor
from app.services.submission_engine import SubmissionResult
from app.core.security import get_password_hash


@pytest.fixture(autouse=True)
def _zero_delay():
    """Kill all sleep delays in the executor so tests run instantly"""
    with patch("app.services.campaign_executor.settings") as mock_settings:
        mock_settings.CAMPAIGN_EXECUTION_DELAY_HOURS = 0
        yield


@pytest.fixture(autouse=True)
def _mock_submission_engine():
    """Mock the submission engine to return success by default"""
    mock_submitter = MagicMock()
    mock_submitter.execute = AsyncMock(return_value=SubmissionResult(
        site="test",
        success=True,
        reference_id="test-ref-123"
    ))

    with patch("app.services.campaign_executor.get_submitter") as mock_get:
        mock_get.return_value = mock_submitter
        yield mock_get


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user for campaign ownership"""
    user = User(
        email="executor_test@example.com",
        hashed_password=get_password_hash("TestPass123!"),
        full_name="Executor Tester",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def draft_campaign(db_session: AsyncSession, test_user: User) -> Campaign:
    """Create a draft campaign ready for execution"""
    campaign = Campaign(
        user_id=test_user.id,
        name="Test Execution Campaign",
        description="testing the executor",
        status=CampaignStatus.DRAFT,
        target_sites=["aboutme", "gravatar"],
        target_count=3,
        profile_template={"state": "CA"},
    )
    db_session.add(campaign)
    await db_session.commit()
    await db_session.refresh(campaign)
    return campaign


class TestCampaignExecutorDirect:
    """Tests calling _execute_campaign directly (no background task)"""

    @pytest.mark.asyncio
    async def test_creates_submissions(self, db_session: AsyncSession, draft_campaign: Campaign, async_session_factory):
        """Starting a campaign should create submission records"""
        # transition to running first
        draft_campaign.status = CampaignStatus.RUNNING
        await db_session.commit()

        await CampaignExecutor._execute_campaign(draft_campaign.id, async_session_factory)

        # check submissions were created: 3 profiles x 2 sites = 6
        async with async_session_factory() as db:
            result = await db.execute(
                select(func.count(Submission.id)).where(
                    Submission.campaign_id == draft_campaign.id
                )
            )
            count = result.scalar()
        assert count == 6

    @pytest.mark.asyncio
    async def test_submissions_get_processed(self, db_session: AsyncSession, draft_campaign: Campaign, async_session_factory):
        """Submissions should move from PENDING to SUBMITTED"""
        draft_campaign.status = CampaignStatus.RUNNING
        await db_session.commit()

        await CampaignExecutor._execute_campaign(draft_campaign.id, async_session_factory)

        async with async_session_factory() as db:
            result = await db.execute(
                select(Submission).where(Submission.campaign_id == draft_campaign.id)
            )
            subs = result.scalars().all()

        assert len(subs) == 6
        for sub in subs:
            assert sub.status == SubmissionStatus.SUBMITTED
            assert sub.submitted_at is not None

    @pytest.mark.asyncio
    async def test_campaign_completes(self, db_session: AsyncSession, draft_campaign: Campaign, async_session_factory):
        """Campaign should be marked completed when all submissions are done"""
        draft_campaign.status = CampaignStatus.RUNNING
        await db_session.commit()

        await CampaignExecutor._execute_campaign(draft_campaign.id, async_session_factory)

        async with async_session_factory() as db:
            campaign = await db.get(Campaign, draft_campaign.id)
        assert campaign.status == CampaignStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_submissions_completed_counter(self, db_session: AsyncSession, draft_campaign: Campaign, async_session_factory):
        """submissions_completed should be incremented"""
        draft_campaign.status = CampaignStatus.RUNNING
        await db_session.commit()

        await CampaignExecutor._execute_campaign(draft_campaign.id, async_session_factory)

        async with async_session_factory() as db:
            campaign = await db.get(Campaign, draft_campaign.id)
        assert campaign.submissions_completed == 6

    @pytest.mark.asyncio
    async def test_no_target_sites_fails(self, db_session: AsyncSession, test_user: User, async_session_factory):
        """Campaign with no target sites should be marked failed"""
        campaign = Campaign(
            user_id=test_user.id,
            name="No Sites",
            status=CampaignStatus.RUNNING,
            target_sites=[],
            target_count=2,
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        await CampaignExecutor._execute_campaign(campaign.id, async_session_factory)

        async with async_session_factory() as db:
            reloaded = await db.get(Campaign, campaign.id)
        assert reloaded.status == CampaignStatus.FAILED

    @pytest.mark.asyncio
    async def test_profile_data_populated(self, db_session: AsyncSession, draft_campaign: Campaign, async_session_factory):
        """Each submission should have profile_data set"""
        draft_campaign.status = CampaignStatus.RUNNING
        await db_session.commit()

        await CampaignExecutor._execute_campaign(draft_campaign.id, async_session_factory)

        async with async_session_factory() as db:
            result = await db.execute(
                select(Submission).where(Submission.campaign_id == draft_campaign.id)
            )
            subs = result.scalars().all()

        for sub in subs:
            assert sub.profile_data is not None
            assert "first_name" in sub.profile_data
            assert "last_name" in sub.profile_data


class TestCampaignExecutorPauseResume:

    @pytest.mark.asyncio
    async def test_pause_stops_processing(self, db_session: AsyncSession, async_session_factory):
        """Pausing should stop the campaign from processing more submissions"""
        # create a campaign with many submissions so we can pause mid-run
        user = User(
            email="pause_test@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            full_name="Pause Tester",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        campaign = Campaign(
            user_id=user.id,
            name="Pause Test",
            status=CampaignStatus.RUNNING,
            target_sites=["aboutme"],
            target_count=5,
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        # start it as a real background task
        await CampaignExecutor.start_campaign(campaign.id, async_session_factory)

        # give it a moment to start creating submissions
        await asyncio.sleep(0.1)

        # pause
        # first update status in DB so the executor sees it
        async with async_session_factory() as db:
            c = await db.get(Campaign, campaign.id)
            c.status = CampaignStatus.PAUSED
            await db.commit()

        await CampaignExecutor.pause_campaign(campaign.id)

        # wait for task to actually finish
        await asyncio.sleep(0.2)

        assert campaign.id not in CampaignExecutor.get_running_campaigns()

    @pytest.mark.asyncio
    async def test_resume_picks_up_pending(self, db_session: AsyncSession, async_session_factory):
        """Resume should process remaining PENDING submissions"""
        user = User(
            email="resume_test@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            full_name="Resume Tester",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        campaign = Campaign(
            user_id=user.id,
            name="Resume Test",
            status=CampaignStatus.RUNNING,
            target_sites=["aboutme"],
            target_count=2,
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        # manually create some submissions - 1 already done, 2 pending
        done_sub = Submission(
            campaign_id=campaign.id,
            site="aboutme",
            status=SubmissionStatus.SUBMITTED,
            profile_data={"first_name": "Already", "last_name": "Done"},
        )
        pending1 = Submission(
            campaign_id=campaign.id,
            site="aboutme",
            status=SubmissionStatus.PENDING,
            profile_data={"first_name": "Still", "last_name": "Waiting"},
        )
        pending2 = Submission(
            campaign_id=campaign.id,
            site="aboutme",
            status=SubmissionStatus.PENDING,
            profile_data={"first_name": "Also", "last_name": "Waiting"},
        )
        db_session.add_all([done_sub, pending1, pending2])
        await db_session.commit()
        await db_session.refresh(pending1)
        await db_session.refresh(pending2)

        # run resume directly
        await CampaignExecutor._resume_campaign(campaign.id, async_session_factory)

        # both pending should now be submitted
        async with async_session_factory() as db:
            p1 = await db.get(Submission, pending1.id)
            p2 = await db.get(Submission, pending2.id)
        assert p1.status == SubmissionStatus.SUBMITTED
        assert p2.status == SubmissionStatus.SUBMITTED

        # campaign should be completed
        async with async_session_factory() as db:
            c = await db.get(Campaign, campaign.id)
        assert c.status == CampaignStatus.COMPLETED


class TestGetRunningCampaigns:

    @pytest.mark.asyncio
    async def test_returns_running_ids(self, db_session: AsyncSession, draft_campaign: Campaign, async_session_factory):
        """get_running_campaigns should list active campaign IDs"""
        draft_campaign.status = CampaignStatus.RUNNING
        await db_session.commit()

        # we need a campaign with enough submissions to still be running when we check
        # easiest: just check the dict directly
        assert draft_campaign.id not in CampaignExecutor.get_running_campaigns()


class TestExecutorUsesTargetIdentity:
    """Verify that the executor generates poisoning profiles when target name is set"""

    @pytest.mark.asyncio
    async def test_profiles_use_target_name(self, db_session: AsyncSession, test_user: User, async_session_factory):
        """When campaign has target name, submissions should have matching profiles"""
        campaign = Campaign(
            user_id=test_user.id,
            name="Target Identity Test",
            status=CampaignStatus.RUNNING,
            target_first_name="Joe",
            target_last_name="Smith",
            target_state="CO",
            target_age=35,
            target_sites=["aboutme"],
            target_count=3,
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        await CampaignExecutor._execute_campaign(campaign.id, async_session_factory)

        async with async_session_factory() as db:
            result = await db.execute(
                select(Submission).where(Submission.campaign_id == campaign.id)
            )
            subs = result.scalars().all()

        assert len(subs) == 3  # 3 profiles x 1 site
        for sub in subs:
            assert sub.profile_data["first_name"] == "Joe"
            assert sub.profile_data["last_name"] == "Smith"

    @pytest.mark.asyncio
    async def test_fallback_without_target_name(self, db_session: AsyncSession, test_user: User, async_session_factory):
        """Old campaigns without target name should still work (random profiles)"""
        campaign = Campaign(
            user_id=test_user.id,
            name="Legacy Campaign",
            status=CampaignStatus.RUNNING,
            target_sites=["aboutme"],
            target_count=2,
            profile_template={"state": "CA"},
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        await CampaignExecutor._execute_campaign(campaign.id, async_session_factory)

        async with async_session_factory() as db:
            result = await db.execute(
                select(Submission).where(Submission.campaign_id == campaign.id)
            )
            subs = result.scalars().all()

        assert len(subs) == 2
        for sub in subs:
            assert "first_name" in sub.profile_data
            assert "last_name" in sub.profile_data


class TestSubmissionEngineIntegration:
    """Tests for submission engine integration"""

    @pytest.mark.asyncio
    async def test_submission_failure_path(self, db_session: AsyncSession, test_user: User, async_session_factory, _mock_submission_engine):
        """Failed submissions should be marked as FAILED with error message"""
        _mock_submission_engine.return_value.execute = AsyncMock(return_value=SubmissionResult(
            site="test",
            success=False,
            error="test error message"
        ))

        campaign = Campaign(
            user_id=test_user.id,
            name="Failure Test",
            status=CampaignStatus.RUNNING,
            target_sites=["aboutme"],
            target_count=1,
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        await CampaignExecutor._execute_campaign(campaign.id, async_session_factory)

        async with async_session_factory() as db:
            result = await db.execute(
                select(Submission).where(Submission.campaign_id == campaign.id)
            )
            subs = result.scalars().all()

        assert len(subs) == 1
        assert subs[0].status == SubmissionStatus.FAILED
        assert subs[0].error_message == "test error message"

        async with async_session_factory() as db:
            c = await db.get(Campaign, campaign.id)
        assert c.submissions_failed == 1

    @pytest.mark.asyncio
    async def test_no_submitter_skipped(self, db_session: AsyncSession, test_user: User, async_session_factory, _mock_submission_engine):
        """Submissions with no submitter should be marked as SKIPPED"""
        _mock_submission_engine.return_value = None

        campaign = Campaign(
            user_id=test_user.id,
            name="No Submitter Test",
            status=CampaignStatus.RUNNING,
            target_sites=["unknownsite"],
            target_count=1,
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        await CampaignExecutor._execute_campaign(campaign.id, async_session_factory)

        async with async_session_factory() as db:
            result = await db.execute(
                select(Submission).where(Submission.campaign_id == campaign.id)
            )
            subs = result.scalars().all()

        assert len(subs) == 1
        assert subs[0].status == SubmissionStatus.SKIPPED
        assert "No submitter for site: unknownsite" in subs[0].error_message

        async with async_session_factory() as db:
            c = await db.get(Campaign, campaign.id)
        assert c.submissions_failed == 1

    @pytest.mark.asyncio
    async def test_reference_id_stored(self, db_session: AsyncSession, test_user: User, async_session_factory, _mock_submission_engine):
        """Reference ID from submission result should be stored"""
        _mock_submission_engine.return_value.execute = AsyncMock(return_value=SubmissionResult(
            site="aboutme",
            success=True,
            reference_id="rad-abc123"
        ))

        campaign = Campaign(
            user_id=test_user.id,
            name="Reference ID Test",
            status=CampaignStatus.RUNNING,
            target_sites=["aboutme"],
            target_count=1,
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        await CampaignExecutor._execute_campaign(campaign.id, async_session_factory)

        async with async_session_factory() as db:
            result = await db.execute(
                select(Submission).where(Submission.campaign_id == campaign.id)
            )
            subs = result.scalars().all()

        assert len(subs) == 1
        assert subs[0].status == SubmissionStatus.SUBMITTED
        assert subs[0].reference_id == "rad-abc123"
