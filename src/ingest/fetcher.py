import time
from typing import Any

import requests

from src.common.config import Settings


def build_headers(settings: Settings) -> dict[str, str]:
    headers = {
        "User-Agent": settings.http_user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-AU,en;q=0.9",
        "Referer": "https://www.realestate.com.au",
    }
    if settings.http_cookie:
        headers["Cookie"] = settings.http_cookie
    return headers


def fetch_html(url: str, settings: Settings, session: requests.Session | None = None) -> str:
    client = session or requests.Session()
    headers = build_headers(settings)
    response = client.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    time.sleep(settings.request_delay_seconds)
    return response.text


def fetch_json(url: str, settings: Settings, session: requests.Session | None = None) -> Any:
    client = session or requests.Session()
    headers = build_headers(settings)
    response = client.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    time.sleep(settings.request_delay_seconds)
    return response.json()
