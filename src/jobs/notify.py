import json
import time
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from src.common.config import load_settings
from src.common.emailer import send_email
from src.common.logging import configure_logging
from src.db.database import (
    get_connection,
    init_db,
    list_saved_searches,
    query_listings,
    update_saved_search_last_run,
)


def run_saved_searches() -> None:
    settings = load_settings()
    conn = get_connection(settings.db_path)
    init_db(conn)
    now = datetime.now(timezone.utc).isoformat()
    saved = list_saved_searches(conn)
    for row in saved:
        criteria = _parse_criteria(row["criteria_json"])
        rows = query_listings(
            conn,
            suburb=criteria.get("suburb"),
            min_price=criteria.get("min_price"),
            max_price=criteria.get("max_price"),
            bedrooms=criteria.get("bedrooms"),
            property_type=criteria.get("property_type"),
            since=row["last_run_at"],
            limit=50,
        )
        if rows:
            body = _format_listing_email(rows, criteria)
            try:
                send_email(
                    settings,
                    row["email"],
                    f"PropertyHunter matches: {row['name']}",
                    body,
                )
            except Exception as exc:
                print(f"Email failed for search {row['id']}: {exc}")
        update_saved_search_last_run(conn, row["id"], now)
    conn.close()


def main() -> None:
    configure_logging()
    _ = load_settings()
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_saved_searches, "interval", hours=24)
    scheduler.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown()


def _parse_criteria(payload: str) -> dict:
    try:
        data = json.loads(payload)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {}


def _format_listing_email(rows: list, criteria: dict) -> str:
    lines = [
        "PropertyHunter matches",
        "",
        f"Suburb: {criteria.get('suburb') or 'any'}",
        f"Min price: {criteria.get('min_price') or 'any'}",
        f"Max price: {criteria.get('max_price') or 'any'}",
        f"Bedrooms: {criteria.get('bedrooms') or 'any'}",
        f"Property type: {criteria.get('property_type') or 'any'}",
        "",
        "Listings:",
    ]
    for row in rows:
        lines.append(f"- {row['title'] or row['address'] or 'Listing'}")
        lines.append(f"  {row['price_text'] or 'Price on request'}")
        lines.append(f"  {row['url']}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
