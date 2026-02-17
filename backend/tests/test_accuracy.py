"""
Tests for the accuracy scoring service, baseline model, and baseline API endpoints
"""

from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_baseline import CampaignBaseline
from app.models.user import User
from app.services.accuracy_service import AccuracyService
from app.services.lookup_service import LookupService
from app.core.security import get_password_hash


# =========================================================================
# Fixtures
# =========================================================================

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        email="accuracy_test@example.com",
        hashed_password=get_password_hash("TestPass123!"),
        full_name="Accuracy Tester",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_campaign(db_session: AsyncSession, test_user: User) -> Campaign:
    campaign = Campaign(
        user_id=test_user.id,
        name="Baseline Test Campaign",
        status=CampaignStatus.RUNNING,
        target_first_name="John",
        target_last_name="Smith",
        target_city="Boston",
        target_state="MA",
        target_age=35,
        target_sites=["radaris"],
        target_count=5,
    )
    db_session.add(campaign)
    await db_session.commit()
    await db_session.refresh(campaign)
    return campaign


def _make_scraper_results(records, source="radaris"):
    """Helper to build a scraper result list in the format LookupService returns"""
    return [
        {
            "source": source,
            "success": True,
            "data": {"results": records},
        }
    ]


# =========================================================================
# AccuracyService unit tests
# =========================================================================

class TestAccuracyServiceAllAccurate:

    def test_all_data_matches(self):
        """When everything matches, score should be 100"""
        real_info = {
            "first_name": "John",
            "last_name": "Smith",
            "city": "Boston",
            "state": "MA",
            "age": 35,
        }
        records = [
            {
                "name": "John Smith",
                "age": 35,
                "addresses": ["123 Main St, Boston, MA 02101"],
                "phone_numbers": [],
                "emails": [],
            }
        ]
        result = AccuracyService.calculate_accuracy(_make_scraper_results(records), real_info)
        assert result["accuracy_score"] == 100.0
        assert result["data_points_total"] == result["data_points_accurate"]
        assert result["data_points_total"] > 0


class TestAccuracyServiceMixed:

    def test_mixed_accuracy(self):
        """Some matching, some not - should return correct percentage"""
        real_info = {
            "first_name": "John",
            "last_name": "Smith",
            "city": "Boston",
            "state": "MA",
            "age": 35,
        }
        records = [
            {
                "name": "John Smith",
                "age": 35,
                "addresses": ["123 Main St, Boston, MA 02101"],
                "phone_numbers": [],
                "emails": [],
            },
            {
                "name": "John Smith",
                "age": 42,  # wrong
                "addresses": ["456 Oak Ave, Denver, CO 80201"],  # wrong
                "phone_numbers": [],
                "emails": [],
            },
        ]
        result = AccuracyService.calculate_accuracy(_make_scraper_results(records), real_info)
        # 2 names match, 1 age matches + 1 wrong, 1 addr matches + 1 wrong
        # total = 2 names + 2 ages + 2 addresses = 6
        # accurate = 2 names + 1 age + 1 address = 4
        assert result["data_points_total"] == 6
        assert result["data_points_accurate"] == 4
        expected_score = round(4 / 6 * 100, 1)
        assert result["accuracy_score"] == expected_score

    def test_age_within_tolerance(self):
        """Age within ±1 should count as accurate"""
        real_info = {"first_name": "Jane", "last_name": "Doe", "age": 30}
        records = [{"name": "Jane Doe", "age": 31}]
        result = AccuracyService.calculate_accuracy(_make_scraper_results(records), real_info)
        assert result["breakdown"]["ages"]["accurate"] == 1

    def test_age_outside_tolerance(self):
        """Age off by more than 1 should not match"""
        real_info = {"first_name": "Jane", "last_name": "Doe", "age": 30}
        records = [{"name": "Jane Doe", "age": 33}]
        result = AccuracyService.calculate_accuracy(_make_scraper_results(records), real_info)
        assert result["breakdown"]["ages"]["accurate"] == 0


class TestAccuracyServiceNoMatches:

    def test_no_matches_except_name(self):
        """Wrong addresses, phones, ages - only name matches"""
        real_info = {
            "first_name": "John",
            "last_name": "Smith",
            "city": "Boston",
            "state": "MA",
            "age": 35,
            "phones": ["5551234567"],
            "emails": ["john@real.com"],
        }
        records = [
            {
                "name": "John Smith",
                "age": 50,
                "addresses": ["999 Fake St, Faketown, TX 77777"],
                "phone_numbers": ["5559999999"],
                "emails": ["wrong@fake.com"],
            }
        ]
        result = AccuracyService.calculate_accuracy(_make_scraper_results(records), real_info)
        # name matches, nothing else does
        assert result["breakdown"]["names"]["accurate"] == 1
        assert result["breakdown"]["addresses"]["accurate"] == 0
        assert result["breakdown"]["ages"]["accurate"] == 0
        assert result["breakdown"]["phones"]["accurate"] == 0
        assert result["breakdown"]["emails"]["accurate"] == 0
        assert result["accuracy_score"] < 100.0

    def test_completely_wrong_name(self):
        """When even the name doesn't match"""
        real_info = {"first_name": "John", "last_name": "Smith"}
        records = [{"name": "Bob Jones", "age": None}]
        result = AccuracyService.calculate_accuracy(_make_scraper_results(records), real_info)
        assert result["breakdown"]["names"]["accurate"] == 0
        assert result["accuracy_score"] == 0.0


class TestAccuracyServiceMissingFields:

    def test_empty_scraper_results(self):
        """No results at all should give 0 total, 0 score"""
        real_info = {"first_name": "John", "last_name": "Smith"}
        result = AccuracyService.calculate_accuracy([], real_info)
        assert result["data_points_total"] == 0
        assert result["accuracy_score"] == 0.0

    def test_failed_source_skipped(self):
        """Failed sources should be ignored"""
        real_info = {"first_name": "John", "last_name": "Smith"}
        results = [{"source": "broken", "success": False, "data": {}}]
        result = AccuracyService.calculate_accuracy(results, real_info)
        assert result["data_points_total"] == 0

    def test_missing_real_info_fields(self):
        """Should handle missing real_info fields gracefully"""
        real_info = {"first_name": "John", "last_name": "Smith"}
        records = [
            {
                "name": "John Smith",
                "age": 35,
                "addresses": ["123 Main St, Boston, MA"],
                "phone_numbers": ["5551234567"],
                "emails": ["john@test.com"],
            }
        ]
        result = AccuracyService.calculate_accuracy(_make_scraper_results(records), real_info)
        # name should match, address won't match (no real city/state)
        # age won't match (no real age), phone/email won't match (no real values)
        assert result["breakdown"]["names"]["accurate"] == 1
        assert result["breakdown"]["addresses"]["accurate"] == 0
        assert result["data_points_total"] > 0

    def test_record_with_no_fields(self):
        """Records with all None/empty fields should contribute nothing"""
        real_info = {"first_name": "John", "last_name": "Smith"}
        records = [{"name": None, "age": None}]
        result = AccuracyService.calculate_accuracy(_make_scraper_results(records), real_info)
        assert result["data_points_total"] == 0


class TestAccuracyServiceBreakdown:

    def test_breakdown_categories(self):
        """Verify all breakdown categories are present"""
        real_info = {"first_name": "John", "last_name": "Smith"}
        result = AccuracyService.calculate_accuracy([], real_info)
        assert "names" in result["breakdown"]
        assert "addresses" in result["breakdown"]
        assert "phones" in result["breakdown"]
        assert "ages" in result["breakdown"]
        assert "emails" in result["breakdown"]
        for cat in result["breakdown"].values():
            assert "total" in cat
            assert "accurate" in cat

    def test_phone_matching(self):
        """Phone numbers should match after normalization"""
        real_info = {
            "first_name": "John",
            "last_name": "Smith",
            "phones": ["(555) 123-4567"],
        }
        records = [
            {
                "name": "John Smith",
                "phone_numbers": ["5551234567"],
            }
        ]
        result = AccuracyService.calculate_accuracy(_make_scraper_results(records), real_info)
        assert result["breakdown"]["phones"]["accurate"] == 1

    def test_email_matching(self):
        """Emails should match case-insensitive"""
        real_info = {
            "first_name": "John",
            "last_name": "Smith",
            "emails": ["John.Smith@Example.COM"],
        }
        records = [
            {
                "name": "John Smith",
                "emails": ["john.smith@example.com"],
            }
        ]
        result = AccuracyService.calculate_accuracy(_make_scraper_results(records), real_info)
        assert result["breakdown"]["emails"]["accurate"] == 1

    def test_location_field_counted(self):
        """The top-level location field should also be counted as an address"""
        real_info = {
            "first_name": "John",
            "last_name": "Smith",
            "city": "Boston",
            "state": "MA",
        }
        records = [
            {
                "name": "John Smith",
                "location": "Boston, MA",
                "addresses": [],
            }
        ]
        result = AccuracyService.calculate_accuracy(_make_scraper_results(records), real_info)
        assert result["breakdown"]["addresses"]["total"] == 1
        assert result["breakdown"]["addresses"]["accurate"] == 1


# =========================================================================
# CampaignBaseline model tests
# =========================================================================

class TestCampaignBaselineModel:

    @pytest.mark.asyncio
    async def test_create_baseline(self, db_session: AsyncSession, test_campaign: Campaign):
        """Should create a baseline with all fields"""
        baseline = CampaignBaseline(
            campaign_id=test_campaign.id,
            snapshot_type="baseline",
            sources_checked=3,
            records_found=12,
            raw_results={"test": "data"},
            accuracy_score=72.5,
            data_points_total=40,
            data_points_accurate=29,
        )
        db_session.add(baseline)
        await db_session.commit()
        await db_session.refresh(baseline)

        assert baseline.id is not None
        assert baseline.campaign_id == test_campaign.id
        assert baseline.snapshot_type == "baseline"
        assert baseline.sources_checked == 3
        assert baseline.records_found == 12
        assert baseline.accuracy_score == 72.5
        assert baseline.data_points_total == 40
        assert baseline.data_points_accurate == 29
        assert baseline.raw_results == {"test": "data"}

    @pytest.mark.asyncio
    async def test_baseline_campaign_relationship(self, db_session: AsyncSession, test_campaign: Campaign):
        """Baseline should link back to its campaign"""
        baseline = CampaignBaseline(
            campaign_id=test_campaign.id,
            snapshot_type="check",
            sources_checked=1,
            records_found=5,
        )
        db_session.add(baseline)
        await db_session.commit()
        await db_session.refresh(baseline)

        assert baseline.campaign_id == test_campaign.id

    @pytest.mark.asyncio
    async def test_snapshot_types(self, db_session: AsyncSession, test_campaign: Campaign):
        """Both baseline and check types should work"""
        b1 = CampaignBaseline(campaign_id=test_campaign.id, snapshot_type="baseline")
        b2 = CampaignBaseline(campaign_id=test_campaign.id, snapshot_type="check")
        db_session.add_all([b1, b2])
        await db_session.commit()

        result = await db_session.execute(
            select(CampaignBaseline).where(CampaignBaseline.campaign_id == test_campaign.id)
        )
        baselines = result.scalars().all()
        types = {b.snapshot_type for b in baselines}
        assert types == {"baseline", "check"}

    @pytest.mark.asyncio
    async def test_nullable_accuracy(self, db_session: AsyncSession, test_campaign: Campaign):
        """accuracy_score should be nullable"""
        baseline = CampaignBaseline(
            campaign_id=test_campaign.id,
            snapshot_type="baseline",
        )
        db_session.add(baseline)
        await db_session.commit()
        await db_session.refresh(baseline)

        assert baseline.accuracy_score is None


# =========================================================================
# API endpoint tests
# =========================================================================

def _mock_search_results():
    """Fake search results for mocking LookupService"""
    return {
        "success": True,
        "query": {"first_name": "John", "last_name": "Smith"},
        "sources_searched": 2,
        "sources_successful": 1,
        "total_records_found": 1,
        "results": [
            {
                "source": "radaris",
                "success": True,
                "data": {
                    "results": [
                        {
                            "name": "John Smith",
                            "age": 35,
                            "addresses": ["123 Main St, Boston, MA 02101"],
                            "phone_numbers": [],
                            "emails": [],
                        }
                    ]
                },
            }
        ],
    }


@pytest.fixture
def auth_headers():
    """Generate a valid JWT token for test requests"""
    from app.core.security import create_access_token
    token = create_access_token(subject="1")
    return {"Authorization": f"Bearer {token}"}


class TestBaselineAPI:

    @pytest.mark.asyncio
    async def test_take_baseline(self, client, db_session, test_user, test_campaign, auth_headers):
        """POST /campaigns/{id}/baseline should create a snapshot"""
        # override the auth to use our test user's ID
        from app.core.security import create_access_token
        token = create_access_token(subject=str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        with patch.object(LookupService, "search_person", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = _mock_search_results()

            resp = await client.post(
                f"/api/v1/campaigns/{test_campaign.id}/baseline",
                headers=headers,
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["snapshot_type"] == "baseline"
        assert data["campaign_id"] == test_campaign.id
        assert data["sources_checked"] == 2
        assert data["records_found"] == 1
        assert data["accuracy_score"] is not None

    @pytest.mark.asyncio
    async def test_take_check(self, client, db_session, test_user, test_campaign, auth_headers):
        """POST /campaigns/{id}/check should create a check snapshot"""
        from app.core.security import create_access_token
        token = create_access_token(subject=str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        with patch.object(LookupService, "search_person", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = _mock_search_results()

            resp = await client.post(
                f"/api/v1/campaigns/{test_campaign.id}/check",
                headers=headers,
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["snapshot_type"] == "check"

    @pytest.mark.asyncio
    async def test_list_baselines(self, client, db_session, test_user, test_campaign, auth_headers):
        """GET /campaigns/{id}/baselines should return all snapshots"""
        from app.core.security import create_access_token
        token = create_access_token(subject=str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        # create a couple baselines directly
        b1 = CampaignBaseline(
            campaign_id=test_campaign.id,
            snapshot_type="baseline",
            sources_checked=2,
            records_found=3,
            accuracy_score=80.0,
            data_points_total=10,
            data_points_accurate=8,
        )
        b2 = CampaignBaseline(
            campaign_id=test_campaign.id,
            snapshot_type="check",
            sources_checked=2,
            records_found=3,
            accuracy_score=60.0,
            data_points_total=10,
            data_points_accurate=6,
        )
        db_session.add_all([b1, b2])
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/campaigns/{test_campaign.id}/baselines",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["baselines"]) == 2

    @pytest.mark.asyncio
    async def test_accuracy_comparison(self, client, db_session, test_user, test_campaign, auth_headers):
        """GET /campaigns/{id}/accuracy should compare baseline vs latest check"""
        from app.core.security import create_access_token
        token = create_access_token(subject=str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        b1 = CampaignBaseline(
            campaign_id=test_campaign.id,
            snapshot_type="baseline",
            sources_checked=2,
            records_found=5,
            accuracy_score=85.0,
            data_points_total=20,
            data_points_accurate=17,
        )
        b2 = CampaignBaseline(
            campaign_id=test_campaign.id,
            snapshot_type="check",
            sources_checked=2,
            records_found=5,
            accuracy_score=55.0,
            data_points_total=20,
            data_points_accurate=11,
        )
        db_session.add_all([b1, b2])
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/campaigns/{test_campaign.id}/accuracy",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["baseline"]["accuracy_score"] == 85.0
        assert data["latest_check"]["accuracy_score"] == 55.0
        assert data["accuracy_change"] == -30.0  # success - accuracy dropped
        assert data["checks_count"] == 1

    @pytest.mark.asyncio
    async def test_accuracy_no_baselines(self, client, db_session, test_user, test_campaign, auth_headers):
        """Accuracy endpoint should work even with no snapshots"""
        from app.core.security import create_access_token
        token = create_access_token(subject=str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get(
            f"/api/v1/campaigns/{test_campaign.id}/accuracy",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["baseline"] is None
        assert data["latest_check"] is None
        assert data["accuracy_change"] is None
        assert data["checks_count"] == 0

    @pytest.mark.asyncio
    async def test_get_baseline_detail(self, client, db_session, test_user, test_campaign, auth_headers):
        """GET /campaigns/{id}/baselines/{baseline_id} should include raw_results"""
        from app.core.security import create_access_token
        token = create_access_token(subject=str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        raw = {"results": [{"name": "John Smith"}]}
        b = CampaignBaseline(
            campaign_id=test_campaign.id,
            snapshot_type="baseline",
            sources_checked=1,
            records_found=1,
            raw_results=raw,
            accuracy_score=100.0,
            data_points_total=1,
            data_points_accurate=1,
        )
        db_session.add(b)
        await db_session.commit()
        await db_session.refresh(b)

        resp = await client.get(
            f"/api/v1/campaigns/{test_campaign.id}/baselines/{b.id}",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["raw_results"] == raw
        assert data["accuracy_score"] == 100.0

    @pytest.mark.asyncio
    async def test_baseline_not_found(self, client, db_session, test_user, test_campaign, auth_headers):
        """Requesting a non-existent baseline should 404"""
        from app.core.security import create_access_token
        token = create_access_token(subject=str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get(
            f"/api/v1/campaigns/{test_campaign.id}/baselines/99999",
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_baseline_campaign_not_found(self, client, db_session, test_user, auth_headers):
        """Taking baseline on non-existent campaign should 404"""
        from app.core.security import create_access_token
        token = create_access_token(subject=str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/campaigns/99999/baseline",
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_baseline_missing_target_name(self, client, db_session, test_user, auth_headers):
        """Campaign without target name should return 400"""
        from app.core.security import create_access_token
        token = create_access_token(subject=str(test_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        campaign = Campaign(
            user_id=test_user.id,
            name="No Target",
            status=CampaignStatus.DRAFT,
            target_sites=["radaris"],
            target_count=5,
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        resp = await client.post(
            f"/api/v1/campaigns/{campaign.id}/baseline",
            headers=headers,
        )
        assert resp.status_code == 400
