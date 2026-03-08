"""
Tests for opt-out execution path in CampaignExecutor.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, CampaignStatus, CampaignType
from app.models.submission import Submission, SubmissionStatus
from app.models.user import User
from app.services.campaign_executor import CampaignExecutor
from app.core.security import get_password_hash


@pytest.fixture(autouse=True)
def _zero_delay():
    with patch("app.services.campaign_executor.settings") as mock_settings:
        mock_settings.CAMPAIGN_EXECUTION_DELAY_HOURS = 0
        yield


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        email="optout_test@example.com",
        hashed_password=get_password_hash("TestPass123!"),
        full_name="Optout Tester",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def running_optout_campaign(db_session: AsyncSession, test_user: User) -> Campaign:
    campaign = Campaign(
        user_id=test_user.id,
        name="Optout Campaign",
        status=CampaignStatus.RUNNING,
        campaign_type=CampaignType.OPTOUT,
        target_first_name="Jane",
        target_last_name="Doe",
        target_city="Austin",
        target_state="TX",
        target_age=36,
        target_sites=["fastpeoplesearch"],
        target_count=1,
    )
    db_session.add(campaign)
    await db_session.commit()
    await db_session.refresh(campaign)
    return campaign


class TestCampaignExecutorOptout:
    @pytest.mark.asyncio
    async def test_execute_optout_success(
        self,
        running_optout_campaign: Campaign,
        async_session_factory,
    ):
        mock_scan = {
            "success": True,
            "results": [
                {
                    "source": "fastpeoplesearch",
                    "success": True,
                    "data": {"results": [{"name": "Jane Doe"}]},
                }
            ],
        }

        mock_handler = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(
                    success=True,
                    removed=True,
                    reference_id="fps-123",
                    error=None,
                )
            )
        )

        with patch(
            "app.services.campaign_executor.LookupService.search_person",
            new=AsyncMock(return_value=mock_scan),
        ), patch(
            "app.services.campaign_executor.get_optout_handler",
            return_value=mock_handler,
        ):
            await CampaignExecutor._execute_campaign(
                running_optout_campaign.id,
                async_session_factory,
            )

        async with async_session_factory() as db:
            campaign = await db.get(Campaign, running_optout_campaign.id)
            count_result = await db.execute(
                select(func.count(Submission.id)).where(
                    Submission.campaign_id == running_optout_campaign.id
                )
            )
            total_submissions = count_result.scalar() or 0
            sub_result = await db.execute(
                select(Submission).where(Submission.campaign_id == running_optout_campaign.id)
            )
            sub = sub_result.scalars().first()

        assert total_submissions == 1
        assert sub.status == SubmissionStatus.REMOVED
        assert sub.reference_id == "fps-123"
        assert campaign.status == CampaignStatus.COMPLETED
        assert campaign.submissions_completed == 1

    @pytest.mark.asyncio
    async def test_execute_optout_no_candidates_fails(
        self,
        running_optout_campaign: Campaign,
        async_session_factory,
    ):
        mock_scan = {"success": True, "results": []}
        with patch(
            "app.services.campaign_executor.LookupService.search_person",
            new=AsyncMock(return_value=mock_scan),
        ):
            await CampaignExecutor._execute_campaign(
                running_optout_campaign.id,
                async_session_factory,
            )

        async with async_session_factory() as db:
            campaign = await db.get(Campaign, running_optout_campaign.id)
            count_result = await db.execute(
                select(func.count(Submission.id)).where(
                    Submission.campaign_id == running_optout_campaign.id
                )
            )
            total_submissions = count_result.scalar() or 0

        assert campaign.status == CampaignStatus.FAILED
        assert total_submissions == 0

    @pytest.mark.asyncio
    async def test_execute_optout_missing_handler_skips_submission(
        self,
        running_optout_campaign: Campaign,
        async_session_factory,
    ):
        mock_scan = {
            "success": True,
            "results": [
                {
                    "source": "fastpeoplesearch",
                    "success": True,
                    "data": {"results": [{"name": "Jane Doe"}]},
                }
            ],
        }

        with patch(
            "app.services.campaign_executor.LookupService.search_person",
            new=AsyncMock(return_value=mock_scan),
        ), patch(
            "app.services.campaign_executor.get_optout_handler",
            return_value=None,
        ):
            await CampaignExecutor._execute_campaign(
                running_optout_campaign.id,
                async_session_factory,
            )

        async with async_session_factory() as db:
            campaign = await db.get(Campaign, running_optout_campaign.id)
            sub_result = await db.execute(
                select(Submission).where(Submission.campaign_id == running_optout_campaign.id)
            )
            sub = sub_result.scalars().first()

        assert sub.status == SubmissionStatus.SKIPPED
        assert campaign.status == CampaignStatus.COMPLETED
        assert campaign.submissions_failed == 1
