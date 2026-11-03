import hmac
import os
import secrets
import tempfile
from getpass import getpass
from pathlib import Path

from app.auth import hash_password, validate_auth_settings

ENV_FILE = Path(__file__).resolve().parent / ".env"


def read_settings(lines: list[str]) -> dict[str, str]:
    settings = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        settings[key.strip()] = value.strip().strip("\"'")
    return settings


def write_settings(lines: list[str], values: dict[str, str]) -> list[str]:
    remaining = set(values)
    updated = []
    for line in lines:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=", 1)[0].strip()
            if key in values:
                updated.append(f"{key}={values[key]}")
                remaining.discard(key)
                continue
        updated.append(line)
    for key in values:
        if key in remaining:
            updated.append(f"{key}={values[key]}")
    return updated


def main() -> None:
    if not ENV_FILE.is_file():
        raise SystemExit(
            "backend/.env is missing. Configure and verify the local MySQL setup first."
        )

    original = ENV_FILE.read_text(encoding="utf-8").splitlines()
    existing = read_settings(original)
    if existing.get("APP_AUTH_REQUIRED", "").lower() in {"1", "true", "yes", "on"}:
        os.environ["APP_AUTH_REQUIRED"] = "true"
        os.environ["APP_SECRET_KEY"] = existing.get("APP_SECRET_KEY", "")
        os.environ["APP_PASSWORD_HASH"] = existing.get("APP_PASSWORD_HASH", "")
        validate_auth_settings()
        print("Password protection is already configured.")
        return

    first = getpass("Choose a private SpendSense sharing password (16+ characters): ")
    second = getpass("Confirm the sharing password: ")
    if not hmac.compare_digest(first.encode("utf-8"), second.encode("utf-8")):
        raise SystemExit("Passwords do not match.")
    if len(first) < 16:
        raise SystemExit("Choose a password with at least 16 characters.")

    values = {
        "APP_AUTH_REQUIRED": "true",
        "APP_SECRET_KEY": secrets.token_urlsafe(48),
        "APP_PASSWORD_HASH": hash_password(first),
    }
    new_contents = "\n".join(write_settings(original, values)) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".env.", suffix=".tmp", dir=ENV_FILE.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as temporary:
            temporary.write(new_contents)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, ENV_FILE)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise

    print("Password protection is enabled. The plaintext password was not saved.")


if __name__ == "__main__":
    main()
