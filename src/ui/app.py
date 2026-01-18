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

    parsed_criteria: SearchCriteria | None = None
    if use_query and query_text:
        parsed_criteria = parse_search_query(query_text)
        suburb = parsed_criteria.suburb or suburb
        min_price = parsed_criteria.min_price or min_price
        max_price = parsed_criteria.max_price or max_price
        bedrooms = parsed_criteria.bedrooms or bedrooms
        property_type = parsed_criteria.property_type or property_type
        st.caption(
            f"Parsed: suburb={suburb}, min_price={min_price}, max_price={max_price}, "
            f"bedrooms={bedrooms}, property_type={property_type}"
        )

    if use_query or use_manual:
        settings = load_settings()
        conn = get_connection(settings.db_path)
        init_db(conn)
        rows = query_listings(
            conn,
            suburb=suburb or None,
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
        st.dataframe([dict(row) for row in rows], use_container_width=True)

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
                "min_price": min_price or None,
                "max_price": max_price or None,
                "bedrooms": bedrooms or None,
                "property_type": property_type or None,
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


if __name__ == "__main__":
    main()
