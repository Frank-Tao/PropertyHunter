PropertyHunter Agent Instructions

Scope
- Build a local-first property ingestion and search system with a Streamlit UI.
- Focus on robust scraping, clean data modeling, and reliable scheduled notifications.

Operating principles
- Follow site terms and legal guidance; implement rate limiting and backoff.
- Prefer resilient parsing: tolerate missing fields and layout changes.
- Keep the MVP small; ship a working vertical slice before expanding.

Tech defaults
- Python 3.11+
- SQLite for MVP; use a DB layer that can migrate to Postgres.
- Requests + BeautifulSoup for HTML parsing (no headless browser unless required).
- Streamlit for UI; FastAPI optional for API layer.
- APScheduler for scheduling; SMTP or SendGrid for email.

Code organization (proposed)
- src/ingest: fetchers, parsers, normalization
- src/db: models, migrations
- src/api: query endpoints
- src/ui: Streamlit app
- src/jobs: scheduled tasks (refresh, notifications)

Quality bar
- Add tests for parsers and criteria-to-query translation.
- Log errors with enough context to replay failures.
- Keep configs in `.env` and do not commit secrets.

Iteration checklist
- Start with one suburb URL and small page count.
- Validate schema with real parsed samples.
- Add a thin search API and Streamlit chat UI.
- Add saved search + email notifications.
