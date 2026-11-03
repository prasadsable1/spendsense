import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from getpass import getpass

PASSWORD_HASH_ITERATIONS = 310_000
TOKEN_LIFETIME_SECONDS = 12 * 60 * 60


def auth_required() -> bool:
    return os.environ.get("APP_AUTH_REQUIRED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def validate_auth_settings() -> None:
    if not auth_required():
        return
    secret = os.environ.get("APP_SECRET_KEY", "")
    encoded_password = os.environ.get("APP_PASSWORD_HASH", "")
    if len(secret) < 32:
        raise RuntimeError(
            "APP_AUTH_REQUIRED is enabled; set APP_SECRET_KEY to at least 32 characters."
        )
    try:
        algorithm, rounds, salt, digest = encoded_password.split("$")
        if algorithm != "pbkdf2_sha256":
            raise ValueError
        iterations = int(rounds)
        if not 100_000 <= iterations <= 2_000_000:
            raise ValueError
        if len(bytes.fromhex(salt)) < 16 or len(bytes.fromhex(digest)) != 32:
            raise ValueError
    except (ValueError, TypeError) as exc:
        raise RuntimeError(
            "APP_AUTH_REQUIRED is enabled; APP_PASSWORD_HASH is missing or invalid. "
            "Generate it with `py -m app.auth` from the backend folder."
        ) from exc


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Choose a password with at least 12 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return (
        f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}"
        f"${salt.hex()}${digest.hex()}"
    )


def verify_password(password: str, encoded_password: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded_password.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(rounds)
        if not 100_000 <= iterations <= 2_000_000:
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        if len(salt) < 16 or len(expected) != 32:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def issue_token(secret: str, now: int | None = None) -> str:
    payload = {
        "sub": "owner",
        "exp": (int(time.time()) if now is None else now)
        + TOKEN_LIFETIME_SECONDS,
    }
    encoded_payload = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).rstrip(b"=").decode("ascii")
    signature = hmac.new(
        secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode(
        "ascii"
    )
    return f"{encoded_payload}.{encoded_signature}"


def verify_token(
    token: str, secret: str, now: int | None = None
) -> bool:
    try:
        encoded_payload, encoded_signature = token.split(".")
        signature = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )
        expected = hmac.new(
            secret.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(signature, expected):
            return False
        payload_bytes = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )
        payload = json.loads(payload_bytes)
        current_time = int(time.time()) if now is None else now
        return (
            payload.get("sub") == "owner"
            and isinstance(payload.get("exp"), int)
            and current_time < payload["exp"]
        )
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return False


if __name__ == "__main__":
    first = getpass("Choose the SpendSense app password (12+ characters): ")
    second = getpass("Confirm the app password: ")
    if not hmac.compare_digest(first, second):
        raise SystemExit("Passwords do not match.")
    try:
        print(hash_password(first))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
