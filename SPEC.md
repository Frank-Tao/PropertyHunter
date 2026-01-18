PropertyHunter - MVP Spec

Goals
- Collect public property listings from realestate.com (no official API).
- Store listings in a local database for fast querying.
- Provide a chatbot-style UI (Streamlit) that understands search criteria, filters the database, and returns a list.
- Allow users to save searches and schedule daily/weekly notifications via email.

Non-goals (MVP)
- Full coverage of all listing types, sold history, or agent portals.
- Real-time streaming or sub-minute refresh.
- User accounts with OAuth/SSO.

Constraints and risks
- Scraping may violate site terms or be blocked by anti-bot measures; require legal review and respectful access patterns.
- Expect layout changes; scraper must be resilient and monitored.
- "No API" means HTML parsing; use caching, rate limits, and backoff.

User stories
- As a buyer, I can describe my desired property in natural language and get matching results.
- As a buyer, I can save a search and get new matches by email daily/weekly.
- As an operator, I can run a scheduled job that refreshes listings and notifies users.

High-level architecture
- Ingestion service: fetches listing pages, parses fields, normalizes and stores in DB.
- Database: local SQLite for MVP; schema designed for easy migration to Postgres.
- API layer: simple query API over the DB (FastAPI or lightweight service).
- Chatbot UI: Streamlit app with chat + filters; calls query API.
- Scheduler: cron or Python scheduler (APScheduler) to run refresh and notification jobs.
- Emailer: SMTP or service provider (SendGrid) for notifications.

Data model (MVP)
Table: listings
- id (text) primary key (derived from site listing id)
- url (text)
- title (text)
- address (text)
- suburb (text)
- state (text)
- postcode (text)
- price_text (text)
- price_min (integer, nullable)
- price_max (integer, nullable)
- bedrooms (integer, nullable)
- bathrooms (integer, nullable)
- parking (integer, nullable)
- property_type (text)
- land_size (integer, nullable)
- listing_status (text)  -- e.g., for_sale, under_offer
- listed_at (datetime, nullable)
- scraped_at (datetime)
- raw_json (text) -- optional for debug

Table: saved_searches
- id (integer) primary key
- name (text)
- criteria_json (text)
- schedule (text) -- daily/weekly
- email (text)
- last_run_at (datetime, nullable)

Ingestion flow (MVP)
- Seed URLs: suburb search or user-provided listing search URLs.
- Fetch pages with rate limit and random delay.
- Parse listing cards and listing detail pages.
- Normalize fields, upsert into listings.

Chatbot flow (MVP)
- User enters criteria in natural language.
- Use lightweight parsing (regex + rules) to convert to structured filters.
- Run DB query; return top N results with short summary.
- Allow user to save the query and schedule notifications.

Notification flow (MVP)
- On schedule, run saved searches.
- Compare against previous results; email new/changed listings.

MVP endpoints
- POST /search (criteria_json) -> list of listings
- POST /saved-search (criteria_json, schedule, email, name)
- POST /run-notifications (manual trigger)

Observability
- Logs for scrape success/fail and parse errors.
- Basic metrics: number of new listings, changed listings, and failed pages.

Security and compliance
- Store user email securely, avoid logging PII.
- Respect robots.txt where possible; use low rate and caching.
- Allow a kill switch to stop scraping if blocked.

Milestones
1) DB schema + ingestion pipeline for a single suburb search.
2) Streamlit UI with manual filters.
3) Chat parser for natural language criteria.
4) Saved searches + scheduler + email notifications.
5) Hardening: retries, backoff, monitoring.
