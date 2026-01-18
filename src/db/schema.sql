CREATE TABLE IF NOT EXISTS listings (
  id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  title TEXT,
  address TEXT,
  suburb TEXT,
  state TEXT,
  postcode TEXT,
  price_text TEXT,
  price_min INTEGER,
  price_max INTEGER,
  bedrooms INTEGER,
  bathrooms INTEGER,
  parking INTEGER,
  property_type TEXT,
  land_size INTEGER,
  listing_status TEXT,
  listed_at TEXT,
  scraped_at TEXT NOT NULL,
  raw_json TEXT
);

CREATE TABLE IF NOT EXISTS saved_searches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  criteria_json TEXT NOT NULL,
  schedule TEXT NOT NULL,
  email TEXT NOT NULL,
  last_run_at TEXT
);
