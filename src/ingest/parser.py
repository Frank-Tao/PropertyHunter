import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Iterable

from bs4 import BeautifulSoup

from src.common.price import parse_price_range
from src.db.database import Listing


def parse_listing_cards(html: str) -> Iterable[Listing]:
    if _is_blocked(html):
        raise ValueError("Blocked by anti-bot page. Provide cookies or try later.")

    soup = BeautifulSoup(html, "html.parser")
    listings: dict[str, Listing] = {}

    argonaut_listings = list(_parse_argonaut_exchange(html))
    for listing in argonaut_listings:
        listings[listing.id] = listing

    if not argonaut_listings:
        for listing in _parse_json_ld(soup):
            listings[listing.id] = listing

        next_data = _load_next_data(soup)
        if next_data:
            for listing in _parse_next_data(next_data):
                listings[listing.id] = listing

    return list(listings.values())


def _is_blocked(html: str) -> bool:
    markers = ["Pardon Our Interruption", "Access Denied", "window.KPSDK={}", "KPSDK.now"]
    return any(marker in html for marker in markers)


def _parse_json_ld(soup: BeautifulSoup) -> Iterable[Listing]:
    listings: list[Listing] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            payload = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        for item in _iter_jsonld_items(payload):
            listing = _listing_from_jsonld_item(item)
            if listing:
                listings.append(listing)
    return listings


def _parse_argonaut_exchange(html: str) -> Iterable[Listing]:
    marker = "window.ArgonautExchange="
    start = html.find(marker)
    if start == -1:
        return []
    start += len(marker)
    end = html.find("</script>", start)
    if end == -1:
        return []

    block = html[start:end].strip()
    if block.endswith(";"):
        block = block[:-1]

    try:
        payload = json.loads(block)
    except json.JSONDecodeError:
        return []

    exchange = payload.get("resi-property_listing-experience-web", {})
    cache_str = exchange.get("urqlClientCache")
    if not cache_str:
        return []

    try:
        cache = json.loads(cache_str)
    except json.JSONDecodeError:
        return []

    listings: list[Listing] = []
    for entry in cache.values():
        data_str = entry.get("data") if isinstance(entry, dict) else None
        if not data_str or "buySearch" not in data_str:
            continue
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        results = data.get("buySearch", {}).get("results", {})
        exact = results.get("exact", {})
        items = exact.get("items", [])
        for item in items:
            listing = _listing_from_argonaut_item(item)
            if listing:
                listings.append(listing)
    return listings


def _iter_jsonld_items(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, list):
        for entry in payload:
            yield from _iter_jsonld_items(entry)
        return
    if not isinstance(payload, dict):
        return
    if payload.get("@type") == "ItemList":
        for element in payload.get("itemListElement", []):
            if isinstance(element, dict) and "item" in element:
                item = element["item"]
                if isinstance(item, dict):
                    yield item
        return
    if payload.get("@type"):
        yield payload


def _listing_from_jsonld_item(item: dict[str, Any]) -> Listing | None:
    url = item.get("url")
    if not url:
        return None

    address = item.get("address")
    address_text = None
    suburb = None
    state = None
    postcode = None
    if isinstance(address, dict):
        address_text = _format_address(address)
        suburb = address.get("addressLocality")
        state = address.get("addressRegion")
        postcode = address.get("postalCode")
    elif isinstance(address, str):
        address_text = address

    price_text = None
    price_min = None
    price_max = None
    offers = item.get("offers")
    if isinstance(offers, dict):
        price = offers.get("price")
        currency = offers.get("priceCurrency")
        if price:
            price_text = f"{currency or ''} {price}".strip()
    if price_text:
        price_min, price_max = parse_price_range(price_text)

    listing_id = _derive_listing_id(item, url)
    return Listing(
        id=listing_id,
        url=url,
        title=item.get("name"),
        address=address_text,
        suburb=suburb,
        state=state,
        postcode=postcode,
        price_text=price_text,
        price_min=price_min,
        price_max=price_max,
        property_type=item.get("@type"),
        scraped_at=now_utc_iso(),
        raw_json=item,
    )


def _listing_from_argonaut_item(item: dict[str, Any]) -> Listing | None:
    if not isinstance(item, dict):
        return None
    listing = item.get("listing")
    if not isinstance(listing, dict):
        return None

    listing_id = listing.get("id")
    link = listing.get("_links", {}).get("canonical", {})
    url = link.get("href")
    if not listing_id or not url:
        return None

    address = listing.get("address", {})
    address_display = address.get("display", {})
    full_address = address_display.get("fullAddress")
    short_address = address_display.get("shortAddress")

    price = listing.get("price", {})
    price_text = price.get("display")
    price_min, price_max = parse_price_range(price_text)
    general = listing.get("generalFeatures", {})
    sizes = listing.get("propertySizes", {})

    return Listing(
        id=str(listing_id),
        url=url,
        title=short_address,
        address=full_address,
        suburb=address.get("suburb"),
        state=address.get("state"),
        postcode=address.get("postcode"),
        price_text=price_text,
        price_min=price_min,
        price_max=price_max,
        bedrooms=_safe_int(general.get("bedrooms", {}).get("value")),
        bathrooms=_safe_int(general.get("bathrooms", {}).get("value")),
        parking=_safe_int(general.get("parkingSpaces", {}).get("value")),
        property_type=listing.get("propertyType", {}).get("display"),
        land_size=_safe_int(_extract_land_size(sizes)),
        scraped_at=now_utc_iso(),
        raw_json=listing,
    )


def _load_next_data(soup: BeautifulSoup) -> dict[str, Any] | None:
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return None
    try:
        return json.loads(script.string)
    except json.JSONDecodeError:
        return None


def _parse_next_data(data: dict[str, Any]) -> Iterable[Listing]:
    listings: list[Listing] = []
    for obj in _walk_json(data):
        candidate = _extract_candidate_listing(obj)
        if candidate:
            listings.append(candidate)
    return listings


def _walk_json(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_json(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_json(item)


def _extract_candidate_listing(data: dict[str, Any]) -> Listing | None:
    url = data.get("seoUrl") or data.get("url") or data.get("listingUrl")
    if url and isinstance(url, str) and url.startswith("/"):
        url = f"https://www.realestate.com.au{url}"

    if not url:
        return None

    listing_id = _derive_listing_id(data, url)
    address_text = data.get("address")
    if isinstance(address_text, dict):
        address_text = _format_address(address_text)

    price_text = data.get("price") or data.get("priceText")
    price_min, price_max = parse_price_range(price_text)
    return Listing(
        id=listing_id,
        url=url,
        title=data.get("displayableAddress") or data.get("title"),
        address=address_text if isinstance(address_text, str) else None,
        suburb=data.get("suburb"),
        state=data.get("state"),
        postcode=data.get("postcode"),
        price_text=price_text,
        price_min=price_min,
        price_max=price_max,
        bedrooms=_safe_int(data.get("bedrooms") or data.get("beds")),
        bathrooms=_safe_int(data.get("bathrooms") or data.get("baths")),
        parking=_safe_int(data.get("parking") or data.get("carSpaces")),
        property_type=data.get("propertyType"),
        land_size=_safe_int(data.get("landSize")),
        listing_status=data.get("status"),
        scraped_at=now_utc_iso(),
        raw_json=data,
    )


def _derive_listing_id(data: dict[str, Any], url: str) -> str:
    for key in ("id", "listingId", "adId", "propertyId"):
        value = data.get(key)
        if isinstance(value, (str, int)) and str(value).strip():
            return str(value)
    match = re.search(r"/property-[^/]+-(\d+)", url)
    if match:
        return match.group(1)
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def _format_address(address: dict[str, Any]) -> str:
    parts = [
        address.get("streetAddress"),
        address.get("addressLocality"),
        address.get("addressRegion"),
        address.get("postalCode"),
    ]
    return ", ".join([part for part in parts if part])


def _extract_land_size(sizes: dict[str, Any]) -> str | None:
    if not isinstance(sizes, dict):
        return None
    land = sizes.get("land") or {}
    value = land.get("displayValue")
    if isinstance(value, str):
        return value
    preferred = sizes.get("preferred") or {}
    if not isinstance(preferred, dict):
        return None
    size = preferred.get("size") or {}
    if not isinstance(size, dict):
        return None
    return size.get("displayValue")


def _safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None




def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
