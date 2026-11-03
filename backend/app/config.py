import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def setting(name: str, default: str) -> str:
    return os.environ.get(name, default)


def database_url() -> str:
    required = ("DB_USER", "DB_PASSWORD", "DB_NAME")
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise RuntimeError(
            "MySQL is not configured. Set " + ", ".join(missing) + " in backend/.env."
        )
    from sqlalchemy import URL

    return URL.create(
        "mysql+pymysql",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=setting("DB_HOST", "127.0.0.1"),
        port=int(setting("DB_PORT", "3306")),
        database=os.environ["DB_NAME"],
        query={"charset": "utf8mb4"},
    ).render_as_string(hide_password=False)


def cors_origins() -> list[str]:
    return [
        origin.strip()
        for origin in setting(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]


def validate_production_cors() -> None:
    auth_enabled = os.environ.get("APP_AUTH_REQUIRED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    origins = [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    if auth_enabled and (
        not origins or any(not origin.startswith("https://") for origin in origins)
    ):
        raise RuntimeError(
            "When APP_AUTH_REQUIRED is enabled, set CORS_ORIGINS to the exact "
            "HTTPS origin(s) of the deployed frontend."
        )
