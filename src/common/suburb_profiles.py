import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.common.config import load_settings
from src.common.geo import haversine_km


@dataclass(frozen=True)
class SuburbProfile:
    suburb: str
    state: str
    latitude: float
    longitude: float
    median_price: int | None
    median_rent: int | None


def load_profiles() -> list[SuburbProfile]:
    settings = load_settings()
    path = None
    if settings.suburb_profiles_path:
        candidate = Path(settings.suburb_profiles_path)
        if candidate.exists():
            path = candidate
    if path is None:
        data_path = Path("data/suburb_profiles.csv")
        if data_path.exists():
            path = data_path
    if path is None:
        path = Path(__file__).with_name("suburb_profiles_sample.csv")
    if not path.exists():
        return []

    profiles: list[SuburbProfile] = []
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                profiles.append(
                    SuburbProfile(
                        suburb=row["suburb"].strip(),
                        state=row.get("state", "").strip(),
                        latitude=float(row["latitude"]),
                        longitude=float(row["longitude"]),
                        median_price=_safe_int(row.get("median_price")),
                        median_rent=_safe_int(row.get("median_rent")),
                    )
                )
            except (KeyError, ValueError):
                continue
    return profiles


def find_profile(suburb: str, profiles: Iterable[SuburbProfile]) -> SuburbProfile | None:
    suburb_lower = suburb.lower()
    for profile in profiles:
        if profile.suburb.lower() == suburb_lower:
            return profile
    return None


def suburbs_within_radius(
    center_suburb: str, radius_km: float, profiles: Iterable[SuburbProfile]
) -> list[SuburbProfile]:
    center = find_profile(center_suburb, profiles)
    if not center:
        return []
    matches: list[SuburbProfile] = []
    for profile in profiles:
        distance = haversine_km(
            center.latitude,
            center.longitude,
            profile.latitude,
            profile.longitude,
        )
        if distance <= radius_km:
            matches.append(profile)
    matches.sort(key=lambda item: item.suburb)
    return matches


def suburb_distance_map(
    center_suburb: str, profiles: Iterable[SuburbProfile]
) -> dict[str, float]:
    center = find_profile(center_suburb, profiles)
    if not center:
        return {}
    distances: dict[str, float] = {}
    for profile in profiles:
        distances[profile.suburb] = haversine_km(
            center.latitude,
            center.longitude,
            profile.latitude,
            profile.longitude,
        )
    return distances


def _safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None
