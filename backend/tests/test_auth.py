import pytest

from app.auth import (
    TOKEN_LIFETIME_SECONDS,
    hash_password,
    issue_token,
    validate_auth_settings,
    verify_password,
    verify_token,
)
from app.config import validate_production_cors


def test_password_hash_verifies_without_storing_plaintext():
    encoded = hash_password("a sufficiently long passphrase")

    assert encoded.startswith("pbkdf2_sha256$")
    assert "a sufficiently long passphrase" not in encoded
    assert verify_password("a sufficiently long passphrase", encoded)
    assert not verify_password("incorrect passphrase", encoded)
    assert not verify_password("anything", "invalid")


def test_password_hash_requires_a_long_password():
    with pytest.raises(ValueError, match="at least 12 characters"):
        hash_password("too-short")


def test_signed_access_token_expires_and_cannot_be_tampered():
    secret = "local-test-secret-that-is-long-enough-123456"
    now = 1_800_000_000
    token = issue_token(secret, now=now)

    assert verify_token(token, secret, now=now)
    assert not verify_token(token, "a different signing secret", now=now)
    assert not verify_token(token + "tampered", secret, now=now)
    assert not verify_token(
        token, secret, now=now + TOKEN_LIFETIME_SECONDS
    )


def test_production_auth_requires_strong_signing_key_and_password_hash(monkeypatch):
    monkeypatch.setenv("APP_AUTH_REQUIRED", "true")
    monkeypatch.setenv("APP_SECRET_KEY", "short")
    monkeypatch.setenv("APP_PASSWORD_HASH", "")
    with pytest.raises(RuntimeError, match="APP_SECRET_KEY"):
        validate_auth_settings()

    monkeypatch.setenv("APP_SECRET_KEY", "a" * 48)
    with pytest.raises(RuntimeError, match="APP_PASSWORD_HASH"):
        validate_auth_settings()

    monkeypatch.setenv("APP_PASSWORD_HASH", hash_password("long enough password"))
    validate_auth_settings()


def test_authenticated_deployment_requires_https_cors_origin(monkeypatch):
    monkeypatch.setenv("APP_AUTH_REQUIRED", "true")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    with pytest.raises(RuntimeError, match="exact HTTPS origin"):
        validate_production_cors()

    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
    with pytest.raises(RuntimeError, match="exact HTTPS origin"):
        validate_production_cors()

    monkeypatch.setenv("CORS_ORIGINS", "https://spendsense.pages.dev")
    validate_production_cors()


def test_authenticated_local_tunnel_uses_same_origin_proxy(monkeypatch):
    monkeypatch.setenv("APP_AUTH_REQUIRED", "true")
    monkeypatch.setenv("APP_ENV", "local_tunnel")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")

    validate_production_cors()
