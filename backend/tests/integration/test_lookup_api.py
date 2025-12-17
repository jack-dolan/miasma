"""
Integration tests for the lookup API endpoints
"""

import pytest
from httpx import AsyncClient


class TestLookupSources:
    """Tests for GET /api/v1/lookup/sources"""

    @pytest.mark.asyncio
    async def test_get_sources_returns_list(self, client: AsyncClient):
        """Should return list of available data sources"""
        response = await client.get("/api/v1/lookup/sources")

        assert response.status_code == 200
        data = response.json()
        assert "sources" in data
        assert isinstance(data["sources"], list)

    @pytest.mark.asyncio
    async def test_sources_have_required_fields(self, client: AsyncClient):
        """Each source should have name, enabled, and display_name"""
        response = await client.get("/api/v1/lookup/sources")

        data = response.json()
        for source in data["sources"]:
            assert "name" in source
            assert "enabled" in source
            assert "display_name" in source


class TestLookupResults:
    """Tests for lookup results CRUD"""

    @pytest.mark.asyncio
    async def test_get_results_empty(self, client: AsyncClient):
        """Should return empty list when no results exist"""
        response = await client.get("/api/v1/lookup/results")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_get_results_pagination(self, client: AsyncClient):
        """Should support pagination parameters"""
        response = await client.get("/api/v1/lookup/results?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "pages" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_result(self, client: AsyncClient):
        """Should return 404 for nonexistent result"""
        response = await client.get("/api/v1/lookup/results/99999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_result(self, client: AsyncClient):
        """Should return 404 when deleting nonexistent result"""
        response = await client.delete("/api/v1/lookup/results/99999")

        assert response.status_code == 404


class TestLookupSearch:
    """Tests for POST /api/v1/lookup/search"""

    @pytest.mark.asyncio
    async def test_search_requires_first_name(self, client: AsyncClient):
        """Should require first_name field"""
        response = await client.post(
            "/api/v1/lookup/search",
            json={"last_name": "Smith"}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_requires_last_name(self, client: AsyncClient):
        """Should require last_name field"""
        response = await client.post(
            "/api/v1/lookup/search",
            json={"first_name": "John"}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_accepts_valid_request(
        self, client: AsyncClient, sample_lookup_request
    ):
        """Should accept valid search request"""
        # Note: This test may timeout or fail if no scrapers are mocked
        # In CI, we should mock the scraper responses
        response = await client.post(
            "/api/v1/lookup/search",
            json={
                "first_name": sample_lookup_request["first_name"],
                "last_name": sample_lookup_request["last_name"],
                "save_results": False,  # Don't save to avoid side effects
            }
        )

        # Should not get validation error
        assert response.status_code != 422


class TestHealthCheck:
    """Tests for health check endpoint"""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Should return healthy status"""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app" in data
        assert "version" in data
