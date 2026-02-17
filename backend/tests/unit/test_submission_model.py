"""
Tests for the Submission model
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.campaign import Campaign, CampaignStatus
from app.models.submission import Submission, SubmissionStatus


@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """Create a user for FK references"""
    user = User(
        email="submitter@example.com",
        hashed_password="fakehash",
        full_name="Test Submitter",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def sample_campaign(db_session: AsyncSession, sample_user: User) -> Campaign:
    """Create a campaign for FK references"""
    campaign = Campaign(
        user_id=sample_user.id,
        name="Poison Campaign",
        status=CampaignStatus.RUNNING,
        target_count=5,
    )
    db_session.add(campaign)
    await db_session.flush()
    return campaign


class TestSubmissionStatus:
    """SubmissionStatus enum values"""

    def test_enum_values(self):
        assert SubmissionStatus.PENDING == "pending"
        assert SubmissionStatus.SUBMITTED == "submitted"
        assert SubmissionStatus.CONFIRMED == "confirmed"
        assert SubmissionStatus.FAILED == "failed"
        assert SubmissionStatus.SKIPPED == "skipped"

    def test_all_values(self):
        values = [s.value for s in SubmissionStatus]
        assert set(values) == {"pending", "submitted", "confirmed", "failed", "skipped"}


class TestSubmissionModel:
    """Tests for creating and querying submissions"""

    @pytest.mark.asyncio
    async def test_create_submission(self, db_session: AsyncSession, sample_campaign: Campaign):
        """Create a submission and verify fields persist"""
        sub = Submission(
            campaign_id=sample_campaign.id,
            site="aboutme",
            status=SubmissionStatus.PENDING,
            profile_data={"first_name": "Jane", "last_name": "Doe", "city": "Austin"},
        )
        db_session.add(sub)
        await db_session.flush()

        assert sub.id is not None
        assert sub.campaign_id == sample_campaign.id
        assert sub.site == "aboutme"
        assert sub.status == SubmissionStatus.PENDING
        assert sub.profile_data["first_name"] == "Jane"
        assert sub.reference_id is None
        assert sub.error_message is None
        assert sub.submitted_at is None

    @pytest.mark.asyncio
    async def test_default_status(self, db_session: AsyncSession, sample_campaign: Campaign):
        """Status should default to PENDING"""
        sub = Submission(
            campaign_id=sample_campaign.id,
            site="gravatar",
            profile_data={"name": "test"},
        )
        db_session.add(sub)
        await db_session.flush()

        assert sub.status == SubmissionStatus.PENDING

    @pytest.mark.asyncio
    async def test_failed_submission(self, db_session: AsyncSession, sample_campaign: Campaign):
        """Should store error details for failed submissions"""
        sub = Submission(
            campaign_id=sample_campaign.id,
            site="aboutme",
            status=SubmissionStatus.FAILED,
            profile_data={"name": "test"},
            error_message="CAPTCHA detected, aborting",
        )
        db_session.add(sub)
        await db_session.flush()

        assert sub.status == SubmissionStatus.FAILED
        assert sub.error_message == "CAPTCHA detected, aborting"

    @pytest.mark.asyncio
    async def test_confirmed_with_reference(self, db_session: AsyncSession, sample_campaign: Campaign):
        """Confirmed submissions should have a reference_id"""
        sub = Submission(
            campaign_id=sample_campaign.id,
            site="gravatar",
            status=SubmissionStatus.CONFIRMED,
            profile_data={"name": "fake person"},
            reference_id="TT-2026-ABC123",
        )
        db_session.add(sub)
        await db_session.flush()

        assert sub.reference_id == "TT-2026-ABC123"
        assert sub.status == SubmissionStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_repr(self, db_session: AsyncSession, sample_campaign: Campaign):
        sub = Submission(
            campaign_id=sample_campaign.id,
            site="aboutme",
            status=SubmissionStatus.SUBMITTED,
            profile_data={},
        )
        db_session.add(sub)
        await db_session.flush()

        r = repr(sub)
        assert "Submission" in r
        assert "aboutme" in r


class TestCampaignSubmissionRelationship:
    """Test the campaign <-> submissions relationship"""

    @pytest.mark.asyncio
    async def test_campaign_has_submissions(self, db_session: AsyncSession, sample_campaign: Campaign):
        """Submissions should be accessible from campaign"""
        for site in ["aboutme", "gravatar", "aboutme"]:
            sub = Submission(
                campaign_id=sample_campaign.id,
                site=site,
                status=SubmissionStatus.PENDING,
                profile_data={"site": site},
            )
            db_session.add(sub)

        await db_session.flush()

        # Access via relationship
        await db_session.refresh(sample_campaign, ["submissions"])
        assert len(sample_campaign.submissions) == 3

    @pytest.mark.asyncio
    async def test_submission_has_campaign(self, db_session: AsyncSession, sample_campaign: Campaign):
        """Submission should reference parent campaign"""
        sub = Submission(
            campaign_id=sample_campaign.id,
            site="aboutme",
            status=SubmissionStatus.PENDING,
            profile_data={},
        )
        db_session.add(sub)
        await db_session.flush()

        await db_session.refresh(sub, ["campaign"])
        assert sub.campaign.id == sample_campaign.id
        assert sub.campaign.name == "Poison Campaign"

    @pytest.mark.asyncio
    async def test_cascade_delete(self, db_session: AsyncSession, sample_user: User):
        """Deleting a campaign should delete its submissions"""
        campaign = Campaign(
            user_id=sample_user.id,
            name="Doomed Campaign",
            status=CampaignStatus.DRAFT,
            target_count=2,
        )
        db_session.add(campaign)
        await db_session.flush()

        sub1 = Submission(
            campaign_id=campaign.id,
            site="aboutme",
            status=SubmissionStatus.PENDING,
            profile_data={"n": 1},
        )
        sub2 = Submission(
            campaign_id=campaign.id,
            site="gravatar",
            status=SubmissionStatus.SUBMITTED,
            profile_data={"n": 2},
        )
        db_session.add_all([sub1, sub2])
        await db_session.flush()

        # Grab IDs before delete
        sub1_id = sub1.id
        sub2_id = sub2.id

        await db_session.delete(campaign)
        await db_session.flush()

        # Submissions should be gone
        result1 = await db_session.get(Submission, sub1_id)
        result2 = await db_session.get(Submission, sub2_id)
        assert result1 is None
        assert result2 is None
