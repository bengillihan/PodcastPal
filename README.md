# PodcastPal

A personal web app that turns Dropbox audio files into podcast RSS feeds, subscribable in any podcast app (Apple Podcasts, Overcast, Pocket Casts, etc.).

---

## What it does

1. Upload audio files to Dropbox and copy their share links.
2. Create a **Feed** in PodcastPal (name, description, optional cover image, retention window).
3. Add **Episodes** to the feed — Dropbox audio URL, title, release date, and an optional **recurring** flag.
4. PodcastPal generates a valid RSS 2.0 / iTunes podcast feed at `/feed/<slug>/rss`.
5. Paste that URL into any podcast app to subscribe.

---

## Stack

| Layer | Technology | Why |
| --- | --- | --- |
| Web framework | Flask | Lightweight; fits a single-user personal app |
| Database | Supabase (PostgreSQL) | Free tier managed Postgres with PgBouncer connection pooling |
| Auth | Google OAuth 2.0 | No password management needed for a personal app |
| Audio storage | Dropbox | Free storage; direct-download links work as RSS enclosures |
| Hosting | Railway | Simple deploy from GitHub on the free tier |

---

## Key design decisions

### NullPool for SQLAlchemy

`app.py` uses `NullPool` instead of a connection pool. Supabase port `6543` is PgBouncer in **transaction mode**, which already manages pooling server-side. Adding a client-side pool on top would waste connections. NullPool opens and closes one connection per request, which is the correct pattern for a PgBouncer transaction-mode setup.

### Two-layer RSS cache

RSS generation is slow because it fetches the file size of every Dropbox audio file over HTTP (required for podcast `<enclosure>` tags). To avoid hitting Dropbox on every subscriber poll, there are two caches:

1. **`RSSCacheManager`** (`cache_manager.py`) — in-memory dict with a 24-hour safety TTL and hourly scheduled refreshes. Checked first; if it hits, no generation happens at all.
2. **`_feed_cache`** (`feed_generator.py`) — secondary in-memory dict inside the generator, also refreshed hourly.

`_invalidate_feed_caches(feed_id)` in `routes.py` clears both whenever a feed or episode is created, edited, or deleted. Both caches use `threading.RLock` because the maintenance background thread runs concurrently with request handlers.

### Recurring episodes

Episodes marked `is_recurring = True` are evergreen — designed to reappear every year (annual sermons, seasonal content, etc.). The stored `release_date` is a stable month/day/time anchor; it does not need to be edited each year. On every hourly RSS refresh, the annual scheduler advances an episode to this year's occurrence once its release time arrives. Until then, the previous year's occurrence remains in the feed so podcast clients are not given a future publication date. The year-specific GUID also changes, causing podcast clients to recognize the new annual occurrence as a new item. Recurring episodes **bypass the retention-period filter** and are always included in the feed regardless of their original date.

Generated feeds include `lastBuildDate`, a 60-minute RSS `ttl`, and HTTP cache revalidation headers. These freshness signals let existing podcast subscriptions discover annual occurrences without requiring listeners to unfollow and refollow the feed.

### Retention period

Each feed has a `retention_period` in days (default 90). Non-recurring episodes older than that window are excluded from the RSS feed. The cutoff is enforced in the SQL query (`query_optimizer.py`) so the database does the filtering, not Python. Each feed can have a different retention period — daily content (Daily Drucker, Daily Tozer) uses 30 days; Bible Biographies uses 365 days.

### Dropbox URL conversion

Dropbox share links (ending in `?dl=0`) don't serve audio directly — podcast apps need a direct-download URL. `utils.py` rewrites them to `dl.dropboxusercontent.com` URLs that stream without redirecting. Conversion happens at episode save time (stored in the DB) and again at RSS generation time as a safety net for any links that slipped through.

### Startup migrations

`app.py` runs idempotent `DO $$ ... END $$` blocks on every startup to add missing columns and drop redundant indexes. No separate migration tool (Alembic, etc.) is needed — Railway deploys just work. Adding new columns in the future means adding another `DO` block here.

### Google OAuth only

No username/password auth. The app is built for one user, so Google OAuth via `google_auth.py` is the simplest secure option.

---

## File structure

```text
app.py                  Flask app factory, DB init, startup migrations
main.py                 Entry point — clears conflicting PG env vars, starts Flask
models.py               SQLAlchemy models: User, Feed, Episode
routes.py               All HTTP route handlers
feed_generator.py       RSS XML generation; recurring episode year-shifting; Dropbox file-size fetching
query_optimizer.py      SQL for RSS queries (respects per-feed retention); LRU-cached count helpers
cache_manager.py        Thread-safe in-memory caches: CacheManager and RSSCacheManager
connection_manager.py   DB session context manager with 30s statement timeout and idle-transaction guard
session_manager.py      Background thread — disposes idle DB connections every 30 min
google_auth.py          Google OAuth blueprint (login, callback, logout)
utils.py                Dropbox URL rewriting helper
start_server.sh         Railway start script — unsets conflicting PG env vars, runs main.py
templates/              Jinja2 HTML templates
static/                 JS and CSS assets
```

---

## Environment variables

Set these in Railway → Variables:

| Variable | Purpose |
| --- | --- |
| `SUPABASE_DB_PASSWORD` | Used by `app.py` to build the DB connection string |
| `DATABASE_URL` | Fallback if `SUPABASE_DB_PASSWORD` is not set |
| `FLASK_SECRET_KEY` | Flask session signing key |
| `GOOGLE_OAUTH_PROD_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_OAUTH_PROD_CLIENT_SECRET` | Google OAuth client secret |
| `SESSION_SECRET` | Additional session secret |

`SUPABASE_DB_HOST`, `SUPABASE_DB_PORT`, `SUPABASE_DB_USER`, and `SUPABASE_DB_NAME` default to the current Supabase project values in `app.py` and can be overridden if the project is migrated.

---

## Database schema

| Table | Key columns |
| --- | --- |
| `user` | `id`, `google_id`, `email`, `name` |
| `feed` | `id`, `user_id`, `name`, `url_slug` (unique), `image_url`, `retention_period`, `last_rss_access` |
| `episode` | `id`, `feed_id`, `title`, `audio_url`, `release_date`, `is_recurring` |

Indexes cover every common query path: `feed.user_id`, `feed.url_slug` (unique constraint creates its own index), and composite `(episode.feed_id, episode.release_date)`.

---

## RSS feed URL

```text
https://<your-railway-domain>/feed/<url-slug>/rss
```

The slug is shown on the feed details page. Use "Regenerate URL" if you need a new one (e.g., after sharing the old one publicly).

---

## CSV bulk upload

Download the template from any feed's detail page. Columns:

```text
title, description, audio_url, release_date, is_recurring
```

- `release_date` format: `YYYY-MM-DD HH:MM` or `MM/DD/YY HH:MM`
- `is_recurring`: `TRUE` or `FALSE`
- `audio_url`: standard Dropbox share link — the app converts it automatically
