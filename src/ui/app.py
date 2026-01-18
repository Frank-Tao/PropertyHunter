import json
import re
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import streamlit as st

from src.common.config import load_settings
from src.common.criteria import SearchCriteria, parse_search_query
from src.common.emailer import send_email
from src.common.suburb_profiles import (
    load_profiles,
    suburb_distance_map,
    suburbs_within_radius,
)
from src.db.database import (
    get_connection,
    init_db,
    list_saved_searches,
    query_listings,
    save_search,
)


def main() -> None:
    st.set_page_config(page_title="PropertyHunter", layout="wide")
    st.title("PropertyHunter")
    st.caption("Search local property listings from your database.")

    with st.sidebar:
        suburb = st.text_input("Suburb")
        radius_km = st.number_input(
            "Radius (km)",
            min_value=0.0,
            step=1.0,
            help="Use with a suburb to search nearby areas.",
        )
        min_price = st.number_input("Min price", min_value=0, step=10000)
        max_price = st.number_input("Max price", min_value=0, step=10000)
        bedrooms = st.number_input("Bedrooms (min)", min_value=0, step=1)
        property_type = st.text_input("Property type")
        limit = st.slider("Results limit", min_value=10, max_value=200, value=50)

    query_text = st.text_input(
        "Describe what you want",
        placeholder="e.g., 3 bed townhouse in Glen Iris under $2m",
    )
    use_query = st.button("Parse + Search")
    use_manual = st.button("Search with filters")
    profiles_only = st.checkbox("Show suburb profiles only (skip listings)")

    parsed_criteria: SearchCriteria | None = None
    nearby_suburbs: list[str] | None = None
    suburb_distances: dict[str, float] = {}
    profiles = []
    if use_query and query_text:
        parsed_criteria = parse_search_query(query_text)
        suburb = parsed_criteria.suburb or suburb
        min_price = parsed_criteria.min_price or min_price
        max_price = parsed_criteria.max_price or max_price
        bedrooms = parsed_criteria.bedrooms or bedrooms
        property_type = parsed_criteria.property_type or property_type
        if parsed_criteria.radius_km:
            radius_km = parsed_criteria.radius_km
        if parsed_criteria.radius_km and parsed_criteria.suburb:
            profiles = load_profiles()
            matches = suburbs_within_radius(
                parsed_criteria.suburb, parsed_criteria.radius_km, profiles
            )
            nearby_suburbs = [profile.suburb for profile in matches]
            suburb_distances = suburb_distance_map(parsed_criteria.suburb, profiles)
        st.caption(
            f"Parsed: suburb={suburb}, min_price={min_price}, max_price={max_price}, "
            f"bedrooms={bedrooms}, property_type={property_type}"
        )

    if use_query or use_manual:
        settings = load_settings()
        conn = get_connection(settings.db_path)
        init_db(conn)
        if not nearby_suburbs and suburb and radius_km and radius_km > 0:
            if not profiles:
                profiles = load_profiles()
            matches = suburbs_within_radius(suburb, radius_km, profiles)
            nearby_suburbs = [profile.suburb for profile in matches]
            suburb_distances = suburb_distance_map(suburb, profiles)
        if suburb:
            if not profiles:
                profiles = load_profiles()
            center_profile = next(
                (profile for profile in profiles if profile.suburb == suburb), None
            )
            if center_profile:
                st.subheader("Suburb profile")
                st.markdown(
                    f"- **{center_profile.suburb}** ({center_profile.state})\n"
                    f"  Median price: {center_profile.median_price or 'n/a'}, "
                    f"Median rent: {center_profile.median_rent or 'n/a'}"
                )

        if nearby_suburbs:
            st.subheader("Nearby suburbs")
            if not profiles:
                profiles = load_profiles()
            nearby_profiles = [
                profile for profile in profiles if profile.suburb in nearby_suburbs
            ]
            st.caption(f"{len(nearby_profiles)} suburbs within radius")
            for profile in nearby_profiles:
                distance = suburb_distances.get(profile.suburb)
                distance_label = f"{distance:.1f} km" if distance is not None else "n/a"
                st.markdown(
                    f"- **{profile.suburb}** ({profile.state}) — {distance_label}\n"
                    f"  Median price: {profile.median_price or 'n/a'}, "
                    f"Median rent: {profile.median_rent or 'n/a'}"
                )

        if not profiles_only:
            rows = query_listings(
                conn,
                suburb=suburb or None,
                suburbs=nearby_suburbs,
                min_price=min_price or None,
                max_price=max_price or None,
                bedrooms=bedrooms or None,
                property_type=property_type or None,
                limit=limit,
            )
            if not rows:
                conn.close()
                st.info("No results yet. Try another filter or ingest data first.")
                return

            st.write(f"Found {len(rows)} listings")
            _render_listings(rows, suburb_distances)

        st.divider()
        st.subheader("Save this search")
        name = st.text_input("Search name", value="Glen Iris search")
        email = st.text_input("Email for alerts")
        schedule = st.selectbox("Schedule", ["daily", "weekly"])
        test_email = st.button("Send test email")
        if test_email:
            if not _is_valid_email(email):
                st.error("Enter a valid email to send a test message.")
            else:
                try:
                    send_email(
                        settings,
                        email,
                        "PropertyHunter test email",
                        "This is a test email from PropertyHunter.",
                    )
                    st.success("Test email sent.")
                except Exception as exc:
                    st.error(f"Test email failed: {exc}")
        if st.button("Save search"):
            if not name.strip():
                st.error("Search name is required.")
                conn.close()
                return
            if not _is_valid_email(email):
                st.error("Enter a valid email to save this search.")
                conn.close()
                return
            criteria = {
                "suburb": suburb or None,
                "suburbs": nearby_suburbs,
                "min_price": min_price or None,
                "max_price": max_price or None,
                "bedrooms": bedrooms or None,
                "property_type": property_type or None,
                "radius_km": parsed_criteria.radius_km if parsed_criteria else None,
            }
            if parsed_criteria:
                criteria["query_text"] = query_text
            search_id = save_search(conn, name, json.dumps(criteria), schedule, email)
            st.success(f"Saved search #{search_id}")

        st.subheader("Saved searches")
        saved = list_saved_searches(conn)
        if saved:
            st.dataframe([dict(row) for row in saved], use_container_width=True)
        else:
            st.caption("No saved searches yet.")
        conn.close()


def _is_valid_email(email: str) -> bool:
    if not email:
        return False
    return re.match(r"^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", email) is not None


def _render_listings(rows: list, suburb_distances: dict[str, float]) -> None:
    for row in rows:
        distance = None
        if row["suburb"]:
            distance = suburb_distances.get(row["suburb"])
        distance_label = f"{distance:.1f} km" if distance is not None else None
        lines = [
            f"**{row['title'] or row['address'] or 'Listing'}**",
            "",
            f"- Price: {row['price_text'] or 'Price on request'}",
            f"- Beds: {row['bedrooms'] or 'n/a'} | Baths: {row['bathrooms'] or 'n/a'} "
            f"| Parking: {row['parking'] or 'n/a'}",
            f"- Address: {row['address'] or 'n/a'}",
        ]
        if distance_label:
            lines.append(f"- Distance: {distance_label}")
        lines.append(f"- URL: {row['url']}")
        st.markdown("\n".join(lines))


if __name__ == "__main__":
    main()
