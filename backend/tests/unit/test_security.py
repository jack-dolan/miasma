"""
Unit tests for security utilities
"""

import pytest
from app.core.security import (
    create_access_token,
    verify_token,
    get_password_hash,
    verify_password,
    validate_password_strength,
)


class TestPasswordHashing:
    """Tests for password hashing"""

    def test_hash_and_verify(self):
        """Should hash and verify correctly"""
        password = "TestPass123!"
        hashed = get_password_hash(password)

        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self):
        """Should fail verification with wrong password"""
        hashed = get_password_hash("CorrectPass1!")
        assert not verify_password("WrongPass1!", hashed)

    def test_different_hashes_each_time(self):
        """Should produce different hashes for same password (salting)"""
        password = "SamePass123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2


class TestJWTTokens:
    """Tests for JWT token creation and verification"""

    def test_create_and_verify_token(self):
        """Should create token and extract subject"""
        token = create_access_token(subject=42)
        subject = verify_token(token)

        assert subject == "42"

    def test_invalid_token_returns_none(self):
        """Should return None for invalid token"""
        result = verify_token("completely.invalid.token")
        assert result is None

    def test_empty_token_returns_none(self):
        """Should return None for empty string"""
        result = verify_token("")
        assert result is None


class TestPasswordValidation:
    """Tests for password strength validation"""

    def test_strong_password(self):
        """Should accept strong password"""
        is_valid, errors = validate_password_strength("Str0ngP@ss!")
        assert is_valid is True
        assert len(errors) == 0

    def test_short_password(self):
        """Should reject short password"""
        is_valid, errors = validate_password_strength("Ab1!")
        assert is_valid is False
        assert any("at least" in e for e in errors)

    def test_no_uppercase(self):
        """Should require uppercase"""
        is_valid, errors = validate_password_strength("alllower1!xx")
        assert is_valid is False

    def test_no_number(self):
        """Should require number"""
        is_valid, errors = validate_password_strength("NoNumbers!!")
        assert is_valid is False

    def test_no_special_char(self):
        """Should require special character"""
        is_valid, errors = validate_password_strength("NoSpecial1x")
        assert is_valid is False
