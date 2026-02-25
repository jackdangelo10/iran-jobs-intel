#!/usr/bin/env bash
# Cloud Run Job mode toggles for the scraper.
#
# Usage:
#   bash docs/cloud_run_job_modes.sh
# or copy/paste individual commands.
#
# Assumes:
#   - Job name: iran-jobs-scraper
#   - Region: us-central1
#   - You are authenticated with gcloud and have the right project set

# 1) NORMAL MODE
# Resume from last successful page (with offset), stop after 5 consecutive
# pages where 100% of URLs are already seen.
gcloud run jobs update iran-jobs-scraper \
  --region us-central1 \
  --set-env-vars \
SCRAPER_FORCE_FULL_CRAWL=false,\
SCRAPER_MAX_CONSECUTIVE_SEEN_PAGES=5,\
SCRAPER_SEEN_RATIO_THRESHOLD=1.0,\
SCRAPER_RESUME_PAGE_OFFSET=-1

# 2) RESUME WITHOUT EARLY STOP
# Resume from last successful page (with offset) but do not stop early based
# on seen pages. It will paginate until "no results" or errors.
gcloud run jobs update iran-jobs-scraper \
  --region us-central1 \
  --set-env-vars \
SCRAPER_FORCE_FULL_CRAWL=false,\
SCRAPER_MAX_CONSECUTIVE_SEEN_PAGES=0,\
SCRAPER_SEEN_RATIO_THRESHOLD=1.0,\
SCRAPER_RESUME_PAGE_OFFSET=-1

# 3) FULL CRAWL
# Start at page 1 and ignore the seen-page early stop logic.
gcloud run jobs update iran-jobs-scraper \
  --region us-central1 \
  --set-env-vars \
SCRAPER_FORCE_FULL_CRAWL=true,\
SCRAPER_MAX_CONSECUTIVE_SEEN_PAGES=5,\
SCRAPER_SEEN_RATIO_THRESHOLD=1.0,\
SCRAPER_RESUME_PAGE_OFFSET=-1
