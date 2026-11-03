import pytest

import setup_public_access
from app.auth import validate_auth_settings, verify_password


def test_setup_stores_only_password_hash_and_signing_key(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DB_HOST=127.0.0.1\nDB_USER=spendsense_app\nDB_PASSWORD=db-secret\nDB_NAME=spendsense\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_public_access, "ENV_FILE", env_file)
    password = "a-private-sharing-passphrase"
    answers = iter([password, password])
    monkeypatch.setattr(setup_public_access, "getpass", lambda _: next(answers))

    setup_public_access.main()

    saved = env_file.read_text(encoding="utf-8")
    settings = setup_public_access.read_settings(saved.splitlines())
    assert settings["APP_AUTH_REQUIRED"] == "true"
    assert len(settings["APP_SECRET_KEY"]) >= 32
    assert verify_password(password, settings["APP_PASSWORD_HASH"])
    assert password not in saved
    assert "db-secret" in saved


def test_setup_rejects_mismatched_passwords_without_writing(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("DB_NAME=spendsense\n", encoding="utf-8")
    original = env_file.read_text(encoding="utf-8")
    monkeypatch.setattr(setup_public_access, "ENV_FILE", env_file)
    answers = iter(["first-password-is-long", "second-password-is-long"])
    monkeypatch.setattr(setup_public_access, "getpass", lambda _: next(answers))

    with pytest.raises(SystemExit, match="Passwords do not match"):
        setup_public_access.main()

    assert env_file.read_text(encoding="utf-8") == original


def test_setup_reuses_existing_valid_protection(tmp_path, monkeypatch):
    from app.auth import hash_password

    env_file = tmp_path / ".env"
    secret = "a-long-enough-test-signing-key-for-local-tunnel"
    env_file.write_text(
        "\n".join(
            [
                "APP_AUTH_REQUIRED=true",
                f"APP_SECRET_KEY={secret}",
                f"APP_PASSWORD_HASH={hash_password('existing private password')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_public_access, "ENV_FILE", env_file)
    monkeypatch.delenv("APP_AUTH_REQUIRED", raising=False)
    monkeypatch.delenv("APP_SECRET_KEY", raising=False)
    monkeypatch.delenv("APP_PASSWORD_HASH", raising=False)

    setup_public_access.main()
    validate_auth_settings()


def test_setup_requires_existing_backend_env(tmp_path, monkeypatch):
    monkeypatch.setattr(
        setup_public_access, "ENV_FILE", tmp_path / "missing.env"
    )

    with pytest.raises(SystemExit, match=r"backend/\.env is missing"):
        setup_public_access.main()
