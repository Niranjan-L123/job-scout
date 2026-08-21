"""Reed.co.uk jobseeker API — one of the largest UK job boards, with good
cyber/security coverage. UK-only, so low US-leak risk.

Dormant until REED_API_KEY is set (free key: https://www.reed.co.uk/developers).
Auth is HTTP Basic with the API key as the username and an empty password.
"""
import os
from datetime import datetime, timedelta

from .. import log
from ..http import get_json
from ..models import Job

API = "https://www.reed.co.uk/api/1.0/search"


def _recent(date_str, max_days):
    """Reed returns the posting date as dd/mm/yyyy; keep only recent ones."""
    try:
        posted = datetime.strptime(date_str, "%d/%m/%Y")
    except (ValueError, TypeError):
        return True  # keep if the date is missing/unparseable
    return posted >= datetime.now() - timedelta(days=max_days)


def fetch(cfg):
    api_key = os.environ.get("REED_API_KEY", "").strip()
    if not api_key:
        log.info("reed: REED_API_KEY not set, skipping "
                 "(free key: https://www.reed.co.uk/developers)")
        return []

    max_days = cfg.get("max_days_old", 7)
    jobs, seen = [], set()
    for query in cfg.get("queries", []):
        params = {
            "keywords": query,
            "locationName": cfg.get("location", "United Kingdom"),
            "resultsToTake": cfg.get("results_per_query", 100),
        }
        try:
            data = get_json(API, params=params, auth=(api_key, ""))
        except Exception as exc:
            log.warning("reed query %r failed: %s", query, exc)
            continue
        for r in data.get("results", []):
            jid = str(r.get("jobId", ""))
            if not jid or jid in seen:
                continue
            if not _recent(r.get("date", ""), max_days):
                continue
            seen.add(jid)
            jobs.append(Job(
                source="reed",
                company=r.get("employerName", ""),
                title=r.get("jobTitle", ""),
                url=r.get("jobUrl", ""),
                location=r.get("locationName", ""),
                posted_at=r.get("date", ""),
                uid=jid,
            ))
    return jobs
