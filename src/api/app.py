from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from src.common.config import load_settings
from src.db.database import get_connection, init_db, query_listings


class SearchRequest(BaseModel):
    suburb: Optional[str] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    bedrooms: Optional[int] = None
    property_type: Optional[str] = None
    limit: int = 50


app = FastAPI(title="PropertyHunter API")


@app.on_event("startup")
def _startup() -> None:
    settings = load_settings()
    conn = get_connection(settings.db_path)
    init_db(conn)
    conn.close()


@app.post("/search")
def search(request: SearchRequest) -> list[dict]:
    settings = load_settings()
    conn = get_connection(settings.db_path)
    rows = query_listings(
        conn,
        suburb=request.suburb,
        min_price=request.min_price,
        max_price=request.max_price,
        bedrooms=request.bedrooms,
        property_type=request.property_type,
        limit=request.limit,
    )
    conn.close()
    return [dict(row) for row in rows]
