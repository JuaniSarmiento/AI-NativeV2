from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password():
    hashed = hash_password("test1234")
    assert verify_password("test1234", hashed)


def test_wrong_password_fails():
    hashed = hash_password("test1234")
    assert not verify_password("wrong", hashed)


def test_hash_is_unique():
    h1 = hash_password("test1234")
    h2 = hash_password("test1234")
    assert h1 != h2  # Different salts


@patch("app.core.security.get_settings")
def test_access_token_contains_required_claims(mock_settings):
    mock_settings.return_value.secret_key = "test-secret"
    mock_settings.return_value.jwt_algorithm = "HS256"
    mock_settings.return_value.jwt_access_token_expire_minutes = 15

    user_id = uuid.uuid4()
    token = create_access_token(user_id, "alumno", jti="test-jti")
    payload = decode_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["role"] == "alumno"
    assert payload["jti"] == "test-jti"
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload


@patch("app.core.security.get_settings")
def test_refresh_token_contains_required_claims(mock_settings):
    mock_settings.return_value.secret_key = "test-secret"
    mock_settings.return_value.jwt_algorithm = "HS256"
    mock_settings.return_value.jwt_refresh_token_expire_days = 7

    user_id = uuid.uuid4()
    token = create_refresh_token(user_id, jti="refresh-jti")
    payload = decode_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["jti"] == "refresh-jti"
    assert payload["type"] == "refresh"
    assert "exp" in payload


@patch("app.core.security.get_settings")
def test_expired_token_raises(mock_settings):
    mock_settings.return_value.secret_key = "test-secret"
    mock_settings.return_value.jwt_algorithm = "HS256"
    mock_settings.return_value.jwt_access_token_expire_minutes = -1  # Already expired

    user_id = uuid.uuid4()
    token = create_access_token(user_id, "alumno")

    from app.core.exceptions import AuthenticationError

    with pytest.raises(AuthenticationError, match="Invalid or expired token"):
        decode_token(token)


@patch("app.core.security.get_settings")
def test_invalid_token_raises(mock_settings):
    mock_settings.return_value.secret_key = "test-secret"
    mock_settings.return_value.jwt_algorithm = "HS256"

    from app.core.exceptions import AuthenticationError

    with pytest.raises(AuthenticationError):
        decode_token("not.a.valid.token")
