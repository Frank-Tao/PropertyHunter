import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Listing:
    id: str
    url: str
    title: str | None = None
    address: str | None = None
    suburb: str | None = None
    state: str | None = None
    postcode: str | None = None
    price_text: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    parking: int | None = None
    property_type: str | None = None
    land_size: int | None = None
    listing_status: str | None = None
    listed_at: str | None = None
    scraped_at: str | None = None
    raw_json: dict[str, Any] | None = None


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    schema_path = Path(__file__).resolve().with_name("schema.sql")
    with schema_path.open("r", encoding="utf-8") as handle:
        conn.executescript(handle.read())
    conn.commit()


def upsert_listings(conn: sqlite3.Connection, listings: Iterable[Listing]) -> int:
    rows = 0
    for listing in listings:
        conn.execute(
            """
            INSERT INTO listings (
              id, url, title, address, suburb, state, postcode, price_text,
              price_min, price_max, bedrooms, bathrooms, parking, property_type,
              land_size, listing_status, listed_at, scraped_at, raw_json
            ) VALUES (
              :id, :url, :title, :address, :suburb, :state, :postcode, :price_text,
              :price_min, :price_max, :bedrooms, :bathrooms, :parking, :property_type,
              :land_size, :listing_status, :listed_at, :scraped_at, :raw_json
            )
            ON CONFLICT(id) DO UPDATE SET
              url=excluded.url,
              title=excluded.title,
              address=excluded.address,
              suburb=excluded.suburb,
              state=excluded.state,
              postcode=excluded.postcode,
              price_text=excluded.price_text,
              price_min=excluded.price_min,
              price_max=excluded.price_max,
              bedrooms=excluded.bedrooms,
              bathrooms=excluded.bathrooms,
              parking=excluded.parking,
              property_type=excluded.property_type,
              land_size=excluded.land_size,
              listing_status=excluded.listing_status,
              listed_at=excluded.listed_at,
              scraped_at=excluded.scraped_at,
              raw_json=excluded.raw_json
            """,
            {
                **listing.__dict__,
                "raw_json": json.dumps(listing.raw_json) if listing.raw_json else None,
            },
        )
        rows += 1
    conn.commit()
    return rows


def query_listings(
    conn: sqlite3.Connection,
    suburb: str | None = None,
    suburbs: list[str] | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    bedrooms: int | None = None,
    property_type: str | None = None,
    since: str | None = None,
    limit: int = 50,
) -> list[sqlite3.Row]:
    clauses: list[str] = []
    params: list[Any] = []

    if suburbs:
        placeholders = ", ".join("?" for _ in suburbs)
        clauses.append(f"suburb IN ({placeholders})")
        params.extend(suburbs)
    elif suburb:
        clauses.append("suburb = ?")
        params.append(suburb)
    if min_price is not None:
        clauses.append("(price_min IS NULL OR price_min >= ?)")
        params.append(min_price)
    if max_price is not None:
        clauses.append("(price_max IS NULL OR price_max <= ?)")
        params.append(max_price)
    if bedrooms is not None:
        clauses.append("(bedrooms IS NULL OR bedrooms >= ?)")
        params.append(bedrooms)
    if property_type:
        clauses.append("property_type = ?")
        params.append(property_type)
    if since:
        clauses.append("scraped_at > ?")
        params.append(since)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT *
        FROM listings
        {where}
        ORDER BY scraped_at DESC
        LIMIT ?
    """
    params.append(limit)
    return list(conn.execute(query, params))


def save_search(
    conn: sqlite3.Connection,
    name: str,
    criteria_json: str,
    schedule: str,
    email: str,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO saved_searches (name, criteria_json, schedule, email)
        VALUES (:name, :criteria_json, :schedule, :email)
        """,
        {
            "name": name,
            "criteria_json": criteria_json,
            "schedule": schedule,
            "email": email,
        },
    )
    conn.commit()
    return int(cursor.lastrowid)


def list_saved_searches(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            """
            SELECT *
            FROM saved_searches
            ORDER BY id DESC
            """
        )
    )


def update_saved_search_last_run(conn: sqlite3.Connection, search_id: int, run_at: str) -> None:
    conn.execute(
        """
        UPDATE saved_searches
        SET last_run_at = :run_at
        WHERE id = :id
        """,
        {"run_at": run_at, "id": search_id},
    )
    conn.commit()
