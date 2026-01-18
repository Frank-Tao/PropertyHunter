import argparse
import re

from src.common.config import Settings, load_settings
from src.common.logging import configure_logging
from src.db.database import get_connection, init_db, upsert_listings
from src.ingest.fetcher import fetch_html
from src.ingest.parser import parse_listing_cards


def run_ingest(seed_url: str, settings: Settings) -> int:
    html = fetch_html(seed_url, settings)
    listings = list(parse_listing_cards(html))

    conn = get_connection(settings.db_path)
    init_db(conn)
    count = upsert_listings(conn, listings)
    conn.close()
    return count


def run_ingest_html(html: str, settings: Settings) -> int:
    listings = list(parse_listing_cards(html))
    conn = get_connection(settings.db_path)
    init_db(conn)
    count = upsert_listings(conn, listings)
    conn.close()
    return count


def run_ingest_pages(seed_url: str, pages: int, start_page: int, settings: Settings) -> int:
    total = 0
    for page in range(start_page, start_page + pages):
        url = _with_page(seed_url, page)
        total += run_ingest(url, settings)
    return total


def _with_page(url: str, page: int) -> str:
    if "list-" in url:
        return _replace_list_page(url, page)
    if url.endswith("/"):
        return f"{url}list-{page}"
    return f"{url}/list-{page}"


def _replace_list_page(url: str, page: int) -> str:
    return re.sub(r"/list-\\d+", f"/list-{page}", url)


def main() -> None:
    configure_logging()
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Run a listing ingest.")
    parser.add_argument(
        "--url",
        default="https://www.realestate.com.au/buy",
        help="Seed search URL to ingest.",
    )
    parser.add_argument(
        "--html-file",
        help="Path to a saved HTML search results page.",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=1,
        help="Number of list pages to ingest (starting from --page-start).",
    )
    parser.add_argument(
        "--page-start",
        type=int,
        default=1,
        help="Start page number for pagination.",
    )
    args = parser.parse_args()
    if args.html_file:
        with open(args.html_file, "r", encoding="utf-8") as handle:
            html = handle.read()
        run_ingest_html(html, settings)
    else:
        run_ingest_pages(args.url, args.pages, args.page_start, settings)


if __name__ == "__main__":
    main()
