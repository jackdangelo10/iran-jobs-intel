# Iran Jobs Intelligence

An end-to-end data pipeline and analytics dashboard that tracks **water-sector job postings in Iran**. Scrapes three Iranian job boards (IranTalent, Jobinja, JobVision) on a recurring schedule, normalizes and enriches the data in PostgreSQL, and exposes the resulting market intelligence through a Next.js web dashboard.

> **Scope note:** As of the Feb 2026 pivot (commit `5ed970c`), the scrapers are filtered to water-sector jobs only — `water` / `water treatment` / `wastewater` (EN) and `آب` / `تصفیه آب` / `فاضلاب` (FA). The schema, processor, and dashboard themselves remain general-purpose; the focus is enforced at scrape time via keyword filters in `src/config/settings.py`.

---

## Goals

1. **Build a longitudinal dataset** of water-related hiring activity in Iran — who is hiring, for what roles, in which cities, with which skill requirements, at what pace.
2. **Normalize across three sites** that publish in Persian with different schemas, so the same company, skill, or location is recognizable everywhere.
3. **Deliver a self-serve dashboard** that surfaces hiring trends, employer concentration, skill demand, and geographic distribution without requiring SQL knowledge.
4. **Run unattended** on a managed schedule, with idempotent re-scrapes and resumable crawls so transient failures don't lose data.

---

## Architecture

```
                                     Cloud Scheduler (nightly)
                                              │
                  ┌───────────────────────────┼───────────────────────────┐
                  ▼                           ▼                           ▼
        ┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
        │  scraper job     │   →    │  processor job   │   →    │  analytics job   │
        │  (Cloud Run)     │        │  (Cloud Run)     │        │  (Cloud Run)     │
        │                  │        │                  │        │                  │
        │ Phase 1: discover│        │ - translate FA→EN│        │ - deactivate     │
        │   URLs (serial)  │        │ - resolve company│        │   stale jobs     │
        │ Phase 2: scrape  │        │ - link location  │        │ - refresh company│
        │   details (6     │        │ - extract 135    │        │   metrics        │
        │   parallel       │        │   skills (EN+FA) │        │ - snapshot stats │
        │   workers)       │        │ - parse salary   │        │                  │
        └────────┬─────────┘        └────────┬─────────┘        └────────┬─────────┘
                 │                           │                           │
                 └───────────────────────────┼───────────────────────────┘
                                             ▼
                                  ┌──────────────────────┐
                                  │  PostgreSQL (Supabase)│
                                  │   public schema       │
                                  └──────────┬───────────┘
                                             │
                                             ▼
                                  ┌──────────────────────┐
                                  │  Next.js dashboard    │
                                  │  (Vercel)             │
                                  │  6 analytics APIs +   │
                                  │  jobs table           │
                                  └──────────────────────┘
```

All three jobs share a single Docker image (`Dockerfile`) and route via `python main.py {scraper|processor|analytics}`. Cloud Build (`cloudbuild.yaml`) builds once and deploys three Cloud Run Jobs with different resource profiles.

---

## Tech stack

| Layer            | Tech                                                          |
|------------------|---------------------------------------------------------------|
| Scraping         | Python 3.12, Selenium (headless Chrome), BeautifulSoup, lxml   |
| Persian NLP      | `hazm`, `deep-translator` (Google), custom skill patterns      |
| Database         | PostgreSQL 15 on Supabase, `psycopg[binary]` + connection pool |
| Job orchestration| GCP Cloud Run Jobs, Cloud Scheduler, Cloud Build, Artifact Registry, Secret Manager |
| Dashboard        | Next.js 14.2 (App Router), TypeScript, Tailwind, Recharts      |
| Dashboard DB     | `postgres` npm driver (lazy-initialized), no Supabase JS       |
| Hosting          | Vercel (dashboard), GCP (pipeline)                             |

---

## Repository layout

```
.
├── main.py                       # Job router — dispatches scraper/processor/analytics
├── Dockerfile                    # Unified image for all three Cloud Run Jobs
├── cloudbuild.yaml               # CI: build once, deploy three jobs
├── requirements.txt
│
├── src/
│   ├── config/settings.py        # Env loading, water-keyword filters, GCP secrets
│   ├── database/
│   │   ├── schema.py             # DDL for 14 tables (public schema)
│   │   ├── connection.py         # Pooled psycopg connection wrapper
│   │   ├── models.py             # Dataclass models
│   │   ├── job_operations.py     # CRUD for job_postings, job_tracking, job_discoveries
│   │   ├── company_operations.py # Company upsert + metrics
│   │   └── scrape_operations.py  # raw_scrapes + scrape_progress
│   ├── scrapers/
│   │   ├── base/                 # base_scraper, driver_manager, rate_limiter
│   │   ├── irantalent/scraper.py
│   │   ├── jobinja/scraper.py
│   │   └── jobvision/scraper.py
│   ├── parallel/                 # worker_pool, job_queue, worker (Phase 2 of scraper)
│   ├── processors/job_processor.py  # translation cache, skill extraction, normalization
│   ├── analytics/engine.py       # deactivation, metric refresh, summary stats
│   ├── runners/
│   │   ├── scraper_job.py        # entrypoint: 2-phase parallel scrape
│   │   ├── processor_job.py      # entrypoint: process pending raw_scrapes
│   │   └── analytics_job.py      # entrypoint: post-cycle metrics
│   └── utils/                    # secrets, logging, hashing
│
├── sql/
│   ├── create_schema.sql
│   └── migrations/
│       ├── 001_create_scraper_role.sql
│       ├── 002_update_scraper_role_password.sql
│       ├── 003_allow_scraper_rls.sql
│       ├── 004_scrape_progress.sql
│       ├── 005_reset_all_data.sql              # ran on water pivot
│       └── 006_drop_aspirational_columns.sql   # schema trim — see below
│
├── dashboard/                    # Next.js 14 app (Vercel root directory)
│   ├── src/app/
│   │   ├── page.tsx              # main dashboard
│   │   ├── layout.tsx
│   │   └── api/                  # stats, jobs-over-time, top-companies,
│   │                             # top-skills, jobs-by-location, breakdowns, jobs
│   ├── src/components/           # FilterBar, StatCard, charts, JobsTable
│   ├── src/lib/db.ts             # lazy `getDb()` postgres client
│   └── next.config.mjs
│
├── tests/                        # pytest suite for database operations
└── docs/                         # operational notes (cloud_run_job_modes.sh, etc.)
```

---

## Database schema

PostgreSQL `public` schema on Supabase. 13 tables. Trimmed in migration 006 to remove aspirational fields no code populated; what remains is what the pipeline actually reads or writes.

**Core entities**
- `job_postings` — one row per `(source_site, external_id)`. Title (FA + EN translation), company/location refs, employment type, experience level, gender/education (scraped, not yet surfaced), salary in original currency, and lifecycle (`first_seen_date`, `last_seen_date`, `is_active`, `deactivated_date`).
- `companies` — canonical employer record with `display_name_persian` + `canonical_name`. Hiring metrics refreshed by `analytics_job`: `total_job_postings`, `active_job_postings`, `hiring_velocity_30d`.
- `locations` — minimal: `city_persian`, `location_normalized` (lowercased dedup key), `location_type`. No province/coords yet.
- `skills` — canonical skill name + category (one of `language` / `framework` / `database` / `cloud` / `tool` / `methodology` / `soft` / `certification` / `domain_knowledge`). Populated from `JobProcessor.SKILL_PATTERNS`.

**Join table**
- `job_skills` — `(job_posting_id, skill_id)` with `requirement_type`, `proficiency_level`, `confidence_score`, `extraction_method`.

**Scraping infrastructure**
- `raw_scrapes` — raw HTML store with content hash + processing status.
- `job_discoveries` — per-session URL discovery log.
- `job_tracking` — per-URL lifecycle (first seen, last seen, disappeared date).
- `company_tracking` — same for company profile URLs.
- `scrape_progress` — per-site resume point so a crashed crawl restarts mid-pagination.
- `translation_cache` — keyed by SHA-256 of source text to avoid re-translating.
- `processing_logs` — structured event log across all three job types.

Key invariant: `job_postings` has `UNIQUE(source_site, external_id)` and all writes go through `ON CONFLICT (...) DO UPDATE`, so re-scraping the same URL refreshes the row instead of duplicating it.

**Schema trim (migration 006).** ~50 columns were dropped across `job_postings`, `companies`, `locations`, `skills`, `job_skills`, `processing_logs`, and `translation_cache`, plus the entirely unused `company_locations` table. Notable removals: sanctions/risk fields on companies, latitude/longitude on locations, IRR↔USD salary conversion fields, hand-tuned `data_quality_score` + `processing_confidence` heuristics, and the dead `dual_use` / `strategic_importance` skill flags. These can be re-added cleanly when there's actual code to populate them.

---

## Pipeline detail

### 1. Scraper (`src/runners/scraper_job.py`)

Two-phase design to keep wall-clock time low while staying polite to upstream sites.

**Phase 1 — discovery (sequential, ~6 min):**
- For each enabled site, walk the public search results paginated.
- Apply the configured water-keyword filter (EN for IranTalent, FA for Jobinja and JobVision).
- Resume from `scrape_progress.last_success_page` unless `SCRAPER_FORCE_FULL_CRAWL=true`.
- Stop early after `SCRAPER_MAX_CONSECUTIVE_SEEN_PAGES` (default 5) pages whose `seen_ratio` exceeds the threshold (default 1.0) — i.e., we've already seen everything on this page.
- Bulk insert into `job_discoveries` + `job_tracking`.

**Phase 2 — parallel detail scrape (~13 min):**
- Pull URLs needing detail from `job_tracking` (limit 10,000).
- Spin up 6 workers, each with its own browser + DB connection.
- Per-site rate limits: 20 req/min for IranTalent + JobVision, 15 for Jobinja.
- Each worker stores raw HTML in `raw_scrapes` with `processing_status='pending'`.

The scraper is **idempotent and resumable**: a mid-run crash leaves the partial work intact, and the next run picks up at `last_success_page`. The unique constraint on `(source_site, external_id)` makes re-scraping safe.

### 2. Processor (`src/runners/processor_job.py` + `src/processors/job_processor.py`)

For each pending row in `raw_scrapes`:
1. Parse HTML → structured `job_postings` row.
2. Translate Persian title + description via Google (cached in `translation_cache` keyed by SHA-256).
3. Normalize:
   - Employment type (full-time, part-time, contract, internship, remote) — maps EN + FA variants.
   - Experience level (entry, mid, senior) — same.
   - Persian numerals → ASCII for salary parsing.
4. Parse salary range from text (handles "از X تا Y تومان" patterns and single-amount "X تومان ماهیانه").
5. Upsert into `companies` (by canonical name) and `locations` (by normalized form).
6. Match against **135 canonical skills** with EN + FA pattern lists (`JobProcessor.SKILL_PATTERNS`). Each entry carries a category so newly-inserted `skills` rows are written with the correct `skill_category` (24 languages, 34 frameworks, 13 databases, 4 cloud platforms, 42 tools, 4 methodologies, 14 domain-knowledge).
7. Insert `job_skills` rows with `confidence_score=0.7` and `extraction_method='keyword_match'`.

### 3. Analytics (`src/runners/analytics_job.py` + `src/analytics/engine.py`)

Runs after every scraper+processor cycle:
- **Deactivate stale jobs** — anything with `last_seen_date` older than 14 days flips to `is_active=false` and gets `deactivated_date=today`.
- **Refresh company metrics** — recompute `active_job_postings` and `hiring_velocity_30d`; zero out metrics for companies whose active count drops to 0.
- **Snapshot summary stats** — logs daily totals into `processing_logs` for trend tracking.

### 4. Dashboard (`dashboard/`)

Next.js 14 App Router app deployed to Vercel with `dashboard/` as the project root.

**API routes** (all `export const dynamic = "force-dynamic"`):
- `GET /api/stats` — total/active jobs, companies, new this week
- `GET /api/jobs-over-time` — time series, grouped by source site
- `GET /api/top-companies` — leaderboard
- `GET /api/top-skills` — most-requested skills
- `GET /api/jobs-by-location` — city/province distribution
- `GET /api/breakdowns` — employment type, experience level, source site
- `GET /api/jobs` — paginated jobs table with filters

**Filters:** `?site=all|irantalent|jobinja|jobvision` and `?range=7|30|90|all` (days).

DB access goes through a lazy `getDb()` singleton in `src/lib/db.ts` using the `postgres` driver (not the Supabase JS client).

---

## Progress

| Component                | Status   | Notes                                                       |
|--------------------------|----------|-------------------------------------------------------------|
| Database schema          | Done     | 13 tables, 6 migrations applied (006 trims aspirational columns) |
| IranTalent scraper       | Done     | Water keyword filtered (EN)                                  |
| Jobinja scraper          | Done     | Water keyword filtered (FA)                                  |
| JobVision scraper        | Done     | Water keyword filtered (FA)                                  |
| Parallel worker pool     | Done     | 6 workers, per-site rate limits                              |
| Resume/skip-seen logic   | Done     | `scrape_progress` table + tunable thresholds                 |
| Translation cache        | Done     | SHA-256 keyed, deduplicates identical strings                |
| Skill extraction         | Done     | 135 canonical skills, EN+FA aliases                          |
| Salary parsing           | Done     | Persian numerals + Toman / range patterns                   |
| Company / location upsert| Done     | Canonical name + normalized location dedup                  |
| Analytics engine         | Done     | 14-day deactivation, metric refresh, summary log             |
| Cloud Build / Cloud Run  | Done     | One image → three Jobs, scheduler-driven                     |
| Dashboard — analytics    | Done     | 6 API routes + Recharts visualizations                       |
| Dashboard — jobs table   | Done     | `/api/jobs` + `JobsTable` component                          |

**Confirmed passing:**
- `npm run build` in `dashboard/` ✓
- `python main.py scraper --dry-run` ✓
- `python main.py processor --dry-run` ✓

---

## Local development

### Prerequisites

- Python 3.12+
- Node 18+
- Chrome/Chromium installed locally (Selenium uses the system browser)
- A Supabase project (or any PostgreSQL 15+ database)

### Pipeline (Python)

```bash
# 1. Install deps
python -m venv .venv
.venv\Scripts\activate                 # Windows
pip install -r requirements.txt

# 2. Configure
cp .env.example .env                   # then edit
# Required: IRAN_JOBS_SCRAPER_DATABASE_URL=postgresql://...

# 3. Initialize schema (one-time)
psql "$IRAN_JOBS_SCRAPER_DATABASE_URL" -f sql/create_schema.sql

# 4. Run a job locally
python main.py scraper
python main.py processor
python main.py analytics

# Dry-run any job (no DB writes, no network)
python main.py scraper --dry-run
```

### Dashboard (Next.js)

```bash
cd dashboard
npm install
echo "DATABASE_URL=postgresql://..." > .env.local
npm run dev                            # http://localhost:3000
```

---

## Configuration

All Python settings live in `src/config/settings.py` and are environment-driven.

**Required**
- `IRAN_JOBS_SCRAPER_DATABASE_URL` — Postgres connection string (local `.env`)
- In Cloud Run: same value stored as `IRAN_JOBS_SCRAPER_DATABASE_URL` in GCP Secret Manager

**Scraping behavior**
- `SCRAPER_DELAY_SECONDS` (default `2`)
- `SCRAPER_MAX_RETRIES` (default `3`)
- `SCRAPER_MAX_CONSECUTIVE_SEEN_PAGES` (default `5`) — stop after N pages of all-seen postings
- `SCRAPER_SEEN_RATIO_THRESHOLD` (default `1.0`) — fraction of a page that must be already-seen to count
- `SCRAPER_RESUME_PAGE_OFFSET` (default `-1`) — `-1` means resume from `scrape_progress`; positive value skips to that page
- `SCRAPER_FORCE_FULL_CRAWL` (default `false`) — bypass resume, crawl from page 1

**Water-sector filtering**
- `SCRAPER_WATER_FOCUS_ENABLED` (default `true`)
- `IRANTALENT_WATER_KEYWORDS_EN` — comma-separated; default `water,water treatment,wastewater`
- `JOBINJA_WATER_KEYWORDS_FA` — default `آب,تصفیه آب,فاضلاب`
- `JOBVISION_WATER_KEYWORDS_FA` — default `آب,تصفیه آب,فاضلاب`

**Selenium**
- `SELENIUM_HEADLESS` (default `true`)
- `SELENIUM_PAGE_LOAD_TIMEOUT` (default `90` seconds)

**GCP**
- `GCP_PROJECT` / `GOOGLE_CLOUD_PROJECT` — required when running in Cloud Run
- `K_SERVICE` or `CLOUD_RUN_JOB` — set automatically by Cloud Run; triggers Secret Manager loading

**Dashboard** (Vercel project env)
- `DATABASE_URL` — same value as `IRAN_JOBS_SCRAPER_DATABASE_URL`

---

## Deployment

### Pipeline (GCP)

Cloud Build trigger on `main` → `cloudbuild.yaml`:
1. Builds one Docker image, tags it `:$SHORT_SHA` and `:latest`.
2. Pushes to Artifact Registry at `us-central1-docker.pkg.dev/$PROJECT_ID/iran-jobs-intel/iran-jobs-scraper`.
3. Deploys three Cloud Run Jobs (all sharing the image, differing in `--args` and resource limits):

| Job                   | Memory | CPU | Timeout | Args        |
|-----------------------|--------|-----|---------|-------------|
| `iran-jobs-scraper`   | 4 GiB  | 2   | 5 hr    | `scraper`   |
| `iran-jobs-processor` | 2 GiB  | 1   | 1 hr    | `processor` |
| `iran-jobs-analytics` | 1 GiB  | 1   | 30 min  | `analytics` |

Runtime service account: `iran-jobs-runtime-sa@$PROJECT_ID.iam.gserviceaccount.com` (has Secret Manager access). Build service account: `iran-jobs-deploy-sa`.

Jobs are triggered nightly via Cloud Scheduler (scraper → processor → analytics).

### Dashboard (Vercel)

- Project root directory: `dashboard`
- Build command: `npm run build`
- Required env var: `DATABASE_URL`

---

## Operational notes

- **`next.config.mjs` (not `.ts`)** — Next.js 14.2 doesn't accept TS config.
- **`serverComponentsExternalPackages`** in Next 14 lives under `experimental`, not at the top level.
- **All API routes export `export const dynamic = "force-dynamic"`** — these are query-time DB reads, not statically generated.
- **`postgres` driver, not Supabase JS client** in the dashboard — Supabase is only the host.
- **`source_site` is always lowercase** (`irantalent`, `jobinja`, `jobvision`) to match the `CHECK` constraint.
- **Migration `005_reset_all_data.sql`** wiped pre-pivot broad-market data when the water focus shipped.

