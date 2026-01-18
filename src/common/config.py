import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    db_path: str
    http_user_agent: str
    request_delay_seconds: float
    http_cookie: str | None
    smtp_host: str | None
    smtp_port: int
    smtp_user: str | None
    smtp_password: str | None
    smtp_from: str | None
    smtp_use_tls: bool
    suburbs_path: str | None


def load_settings() -> Settings:
    load_dotenv()
    db_path = os.getenv("DB_PATH", "data/propertyhunter.db")
    http_user_agent = os.getenv(
        "HTTP_USER_AGENT", "PropertyHunterBot/0.1 (+contact@example.com)"
    )
    request_delay_seconds = float(os.getenv("REQUEST_DELAY_SECONDS", "1.5"))
    http_cookie = os.getenv("HTTP_COOKIE") or None
    smtp_host = os.getenv("SMTP_HOST") or None
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER") or None
    smtp_password = os.getenv("SMTP_PASSWORD") or None
    smtp_from = os.getenv("SMTP_FROM") or None
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}
    suburbs_path = os.getenv("SUBURBS_PATH") or None
    return Settings(
        db_path=db_path,
        http_user_agent=http_user_agent,
        request_delay_seconds=request_delay_seconds,
        http_cookie=http_cookie,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        smtp_from=smtp_from,
        smtp_use_tls=smtp_use_tls,
        suburbs_path=suburbs_path,
    )
