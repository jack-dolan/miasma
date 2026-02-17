"""
Integration tests for authentication endpoints
"""

import pytest
from httpx import AsyncClient


class TestRegister:
    """Tests for POST /api/v1/auth/register"""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient, sample_user_data):
        """Should create a new user"""
        response = await client.post("/api/v1/auth/register", json=sample_user_data)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == sample_user_data["email"]
        assert data["full_name"] == sample_user_data["full_name"]
        assert data["is_active"] is True
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, sample_user_data):
        """Should reject duplicate email"""
        await client.post("/api/v1/auth/register", json=sample_user_data)
        response = await client.post("/api/v1/auth/register", json=sample_user_data)

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """Should reject weak passwords"""
        response = await client.post("/api/v1/auth/register", json={
            "email": "weak@test.com",
            "password": "abc",
            "full_name": "Weak Pass",
        })

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_missing_email(self, client: AsyncClient):
        """Should require email"""
        response = await client.post("/api/v1/auth/register", json={
            "password": "SecurePass123!",
        })

        assert response.status_code == 422


class TestLogin:
    """Tests for POST /api/v1/auth/login"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, sample_user_data):
        """Should return tokens on valid login"""
        await client.post("/api/v1/auth/register", json=sample_user_data)

        response = await client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"],
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == sample_user_data["email"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, sample_user_data):
        """Should reject wrong password"""
        await client.post("/api/v1/auth/register", json=sample_user_data)

        response = await client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "password": "WrongPass123!",
        })

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Should reject login for non-existent user"""
        response = await client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "SomePass123!",
        })

        assert response.status_code == 401


class TestDemoLogin:
    """Tests for POST /api/v1/auth/demo-login"""

    @pytest.mark.asyncio
    async def test_demo_login(self, client: AsyncClient):
        """Should return valid tokens"""
        response = await client.post("/api/v1/auth/demo-login")

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "demo@miasma.dev"


class TestAuthMe:
    """Tests for GET /api/v1/auth/me"""

    @pytest.mark.asyncio
    async def test_me_requires_auth(self, client: AsyncClient):
        """Should return 403 without token"""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_me_with_valid_token(self, client: AsyncClient, sample_user_data):
        """Should return user data with valid token"""
        await client.post("/api/v1/auth/register", json=sample_user_data)
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"],
        })
        token = login_resp.json()["access_token"]

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["email"] == sample_user_data["email"]

    @pytest.mark.asyncio
    async def test_me_with_invalid_token(self, client: AsyncClient):
        """Should reject invalid token"""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token-here"}
        )

        assert response.status_code == 401
