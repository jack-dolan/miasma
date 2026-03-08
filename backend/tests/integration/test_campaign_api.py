"""
Integration tests for campaign endpoints
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


async def get_auth_token(client: AsyncClient) -> str:
    """Helper to get a valid auth token"""
    resp = await client.post("/api/v1/auth/demo-login")
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestCampaignList:
    """Tests for GET /api/v1/campaigns/"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        """Should require authentication"""
        response = await client.get("/api/v1/campaigns/")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_empty_list(self, client: AsyncClient):
        """Should return empty list initially"""
        token = await get_auth_token(client)
        response = await client.get("/api/v1/campaigns/", headers=auth_headers(token))

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0


class TestCampaignCreate:
    """Tests for POST /api/v1/campaigns/"""

    @pytest.mark.asyncio
    async def test_create_campaign(self, client: AsyncClient):
        """Should create a new campaign"""
        token = await get_auth_token(client)
        response = await client.post(
            "/api/v1/campaigns/",
            headers=auth_headers(token),
            json={
                "name": "Test Campaign",
                "description": "Testing data injection",
                "target_first_name": "Joe",
                "target_last_name": "Smith",
                "target_count": 5,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Campaign"
        assert data["status"] == "draft"
        assert data["campaign_type"] == "poisoning"
        assert data["target_count"] == 5
        assert data["target_first_name"] == "Joe"
        assert data["target_last_name"] == "Smith"

    @pytest.mark.asyncio
    async def test_create_campaign_with_optout_type(self, client: AsyncClient):
        """Should accept explicit campaign_type"""
        token = await get_auth_token(client)
        response = await client.post(
            "/api/v1/campaigns/",
            headers=auth_headers(token),
            json={
                "name": "Optout Campaign",
                "target_first_name": "Jane",
                "target_last_name": "Doe",
                "campaign_type": "optout",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["campaign_type"] == "optout"

    @pytest.mark.asyncio
    async def test_create_campaign_with_full_target(self, client: AsyncClient):
        """Should store all target identity fields"""
        token = await get_auth_token(client)
        response = await client.post(
            "/api/v1/campaigns/",
            headers=auth_headers(token),
            json={
                "name": "Full Target Campaign",
                "target_first_name": "Jane",
                "target_last_name": "Doe",
                "target_city": "Denver",
                "target_state": "CO",
                "target_age": 35,
                "target_count": 10,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["target_first_name"] == "Jane"
        assert data["target_last_name"] == "Doe"
        assert data["target_city"] == "Denver"
        assert data["target_state"] == "CO"
        assert data["target_age"] == 35

    @pytest.mark.asyncio
    async def test_create_requires_name(self, client: AsyncClient):
        """Should require campaign name"""
        token = await get_auth_token(client)
        response = await client.post(
            "/api/v1/campaigns/",
            headers=auth_headers(token),
            json={
                "description": "no name",
                "target_first_name": "Joe",
                "target_last_name": "Smith",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_requires_target_name(self, client: AsyncClient):
        """Should require target first and last name"""
        token = await get_auth_token(client)
        response = await client.post(
            "/api/v1/campaigns/",
            headers=auth_headers(token),
            json={"name": "Missing Target"},
        )

        assert response.status_code == 422


class TestCampaignCRUD:
    """Tests for campaign CRUD operations"""

    @pytest.mark.asyncio
    async def test_get_campaign(self, client: AsyncClient):
        """Should retrieve a specific campaign"""
        token = await get_auth_token(client)

        # Create
        create_resp = await client.post(
            "/api/v1/campaigns/",
            headers=auth_headers(token),
            json={"name": "Get Test", "target_first_name": "A", "target_last_name": "B"},
        )
        campaign_id = create_resp.json()["id"]

        # Get
        response = await client.get(
            f"/api/v1/campaigns/{campaign_id}",
            headers=auth_headers(token),
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Get Test"

    @pytest.mark.asyncio
    async def test_update_campaign(self, client: AsyncClient):
        """Should update campaign fields"""
        token = await get_auth_token(client)

        create_resp = await client.post(
            "/api/v1/campaigns/",
            headers=auth_headers(token),
            json={"name": "Original Name", "target_first_name": "A", "target_last_name": "B"},
        )
        campaign_id = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/campaigns/{campaign_id}",
            headers=auth_headers(token),
            json={"name": "Updated Name", "campaign_type": "optout"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        assert response.json()["campaign_type"] == "optout"

    @pytest.mark.asyncio
    async def test_delete_campaign(self, client: AsyncClient):
        """Should delete a campaign"""
        token = await get_auth_token(client)

        create_resp = await client.post(
            "/api/v1/campaigns/",
            headers=auth_headers(token),
            json={"name": "Delete Me", "target_first_name": "A", "target_last_name": "B"},
        )
        campaign_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/campaigns/{campaign_id}",
            headers=auth_headers(token),
        )

        assert response.status_code == 200

        # Verify it's gone
        get_resp = await client.get(
            f"/api/v1/campaigns/{campaign_id}",
            headers=auth_headers(token),
        )
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_status_transition(self, client: AsyncClient):
        """Should allow valid status transitions"""
        token = await get_auth_token(client)

        create_resp = await client.post(
            "/api/v1/campaigns/",
            headers=auth_headers(token),
            json={"name": "Status Test", "target_first_name": "A", "target_last_name": "B"},
        )
        campaign_id = create_resp.json()["id"]

        # draft -> running
        response = await client.patch(
            f"/api/v1/campaigns/{campaign_id}",
            headers=auth_headers(token),
            json={"status": "running"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "running"

    @pytest.mark.asyncio
    async def test_invalid_status_transition(self, client: AsyncClient):
        """Should reject invalid status transitions"""
        token = await get_auth_token(client)

        create_resp = await client.post(
            "/api/v1/campaigns/",
            headers=auth_headers(token),
            json={"name": "Invalid Transition", "target_first_name": "A", "target_last_name": "B"},
        )
        campaign_id = create_resp.json()["id"]

        # draft -> completed (not allowed)
        response = await client.patch(
            f"/api/v1/campaigns/{campaign_id}",
            headers=auth_headers(token),
            json={"status": "completed"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_nonexistent_campaign(self, client: AsyncClient):
        """Should return 404 for missing campaign"""
        token = await get_auth_token(client)
        response = await client.get(
            "/api/v1/campaigns/99999",
            headers=auth_headers(token),
        )
        assert response.status_code == 404


class TestCampaignScan:
    """Tests for POST /api/v1/campaigns/{id}/scan"""

    @pytest.mark.asyncio
    async def test_scan_optout_campaign(self, client: AsyncClient):
        token = await get_auth_token(client)
        create_resp = await client.post(
            "/api/v1/campaigns/",
            headers=auth_headers(token),
            json={
                "name": "Scan Campaign",
                "target_first_name": "Jane",
                "target_last_name": "Doe",
                "target_city": "Austin",
                "target_state": "TX",
                "campaign_type": "optout",
                "target_sites": ["fastpeoplesearch"],
            },
        )
        campaign_id = create_resp.json()["id"]

        mock_scan = {
            "sources_searched": 1,
            "sources_successful": 1,
            "total_records_found": 2,
            "results": [
                {
                    "source": "fastpeoplesearch",
                    "success": True,
                    "data": {"results": [{"name": "Jane Doe", "location": "Austin, TX"}]},
                }
            ],
        }

        with patch(
            "app.api.routes.campaigns.LookupService.search_person",
            new=AsyncMock(return_value=mock_scan),
        ):
            response = await client.post(
                f"/api/v1/campaigns/{campaign_id}/scan",
                headers=auth_headers(token),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["campaign_id"] == campaign_id
        assert data["sources_searched"] == 1
        assert data["sources_successful"] == 1
        assert data["total_records_found"] == 2
        assert len(data["candidates"]) == 1
        assert data["candidates"][0]["site"] == "fastpeoplesearch"
        assert len(data["candidates"][0]["preview_records"]) == 1

        campaign_resp = await client.get(
            f"/api/v1/campaigns/{campaign_id}",
            headers=auth_headers(token),
        )
        assert campaign_resp.status_code == 200
        campaign_data = campaign_resp.json()
        assert campaign_data["last_scan_at"] is not None
        assert campaign_data["last_scan_result"] is not None
        assert campaign_data["last_scan_result"]["total_records_found"] == 2

    @pytest.mark.asyncio
    async def test_scan_rejects_non_optout_campaign(self, client: AsyncClient):
        token = await get_auth_token(client)
        create_resp = await client.post(
            "/api/v1/campaigns/",
            headers=auth_headers(token),
            json={
                "name": "Poisoning Campaign",
                "target_first_name": "Jane",
                "target_last_name": "Doe",
                "campaign_type": "poisoning",
            },
        )
        campaign_id = create_resp.json()["id"]

        response = await client.post(
            f"/api/v1/campaigns/{campaign_id}/scan",
            headers=auth_headers(token),
        )
        assert response.status_code == 400
