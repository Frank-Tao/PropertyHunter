import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from src.common.price import parse_price_range


@dataclass(frozen=True)
class SearchCriteria:
    suburb: str | None
    min_price: int | None
    max_price: int | None
    bedrooms: int | None
    property_type: str | None


PROPERTY_TYPE_KEYWORDS = {
    "house": "House",
    "townhouse": "Townhouse",
    "apartment": "Apartment",
    "unit": "Unit",
    "villa": "Villa",
    "land": "Land",
}


def parse_search_query(text: str) -> SearchCriteria:
    suburb = _match_suburb_from_list(text) or _extract_suburb(text)
    bedrooms = _extract_bedrooms(text)
    property_type = _extract_property_type(text)
    price_phrase = _extract_price_phrase(text)
    min_price, max_price = parse_price_range(price_phrase) if price_phrase else (None, None)
    return SearchCriteria(
        suburb=suburb,
        min_price=min_price,
        max_price=max_price,
        bedrooms=bedrooms,
        property_type=property_type,
    )


def _extract_suburb(text: str) -> str | None:
    match = re.search(
        r"\bin\s+([a-zA-Z\s]+?)(?=(?:,|\bunder\b|\bover\b|\bfrom\b|\bbetween\b|\bwith\b|$))",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    suburb = match.group(1).strip()
    if not suburb:
        return None
    return _titlecase_words(suburb)


def _match_suburb_from_list(text: str) -> str | None:
    suburbs = _load_suburbs()
    lowered = text.lower()
    matches: list[str] = []
    for suburb in suburbs:
        pattern = rf"\b{re.escape(suburb.lower())}\b"
        if re.search(pattern, lowered):
            matches.append(suburb)
    if not matches:
        return None
    return max(matches, key=len)


def _extract_bedrooms(text: str) -> int | None:
    matches = re.findall(
        r"(\d+)\s*(?:bed|beds|bedroom|bedrooms)\b", text, re.IGNORECASE
    )
    if not matches:
        return None
    return max(int(value) for value in matches)


def _extract_property_type(text: str) -> str | None:
    lowered = text.lower()
    for keyword, label in PROPERTY_TYPE_KEYWORDS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            return label
    return None


def _extract_price_phrase(text: str) -> str | None:
    lowered = text.lower()
    patterns = [
        r"(?:under|over|from|between|up to|maximum)\s+\$?\s*\d[\d,.]*\s*[mk]?"
        r"(?:\s*(?:-|to|and)\s*\$?\s*\d[\d,.]*\s*[mk]?)?",
        r"\$\s*\d[\d,.]*\s*[mk]?(?:\s*(?:-|to|and)\s*\$?\s*\d[\d,.]*\s*[mk]?)?",
        r"\d+(?:\.\d+)?\s*[mk]\b(?:\s*(?:-|to|and)\s*\d+(?:\.\d+)?\s*[mk])?",
    ]
    for pattern in patterns:
        match = re.search(pattern, lowered)
        if match:
            return match.group(0)
    return None


def _titlecase_words(text: str) -> str:
    return " ".join(word.capitalize() for word in text.split())


@lru_cache(maxsize=1)
def _load_suburbs() -> list[str]:
    suburbs: list[str] = []
    default_path = Path(__file__).with_name("suburbs_vic.txt")
    _load_suburbs_from_path(default_path, suburbs)
    extra_path = _load_extra_suburbs_path()
    if extra_path:
        _load_suburbs_from_path(extra_path, suburbs)
    return suburbs


def _load_extra_suburbs_path() -> Path | None:
    from src.common.config import load_settings

    settings = load_settings()
    if not settings.suburbs_path:
        return None
    path = Path(settings.suburbs_path)
    return path if path.exists() else None


def _load_suburbs_from_path(path: Path, suburbs: list[str]) -> None:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            value = line.strip()
            if value and value not in suburbs:
                suburbs.append(value)
