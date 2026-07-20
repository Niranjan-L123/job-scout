import os

from .. import log
from ..http import get_json
from ..models import Job

API = "https://api.adzuna.com/v1/api/jobs/gb/search/1"


def fetch(cfg):
    app_id = os.environ.get("ADZUNA_APP_ID", "").strip()
    app_key = os.environ.get("ADZUNA_APP_KEY", "").strip()
    if not app_id or not app_key:
        log.info("adzuna: ADZUNA_APP_ID/ADZUNA_APP_KEY not set, skipping "
                 "(free key: https://developer.adzuna.com)")
        return []

    jobs, seen_ids = [], set()
    for query in cfg.get("queries", []):
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": 50,
            "max_days_old": cfg.get("max_days_old", 3),
            "sort_by": "date",
        }
        # A query is either a plain string (title search) or a mapping of raw
        # Adzuna API params (e.g. what_or + category for a broad sweep).
        if isinstance(query, dict):
            params.update(query)
        else:
            params["what"] = query
        try:
            data = get_json(API, params=params)
        except Exception as exc:
            log.warning("adzuna query %r failed: %s", query, exc)
            continue
        for r in data.get("results", []):
            # redirect_url carries per-request tracking tokens; the ad id is
            # the stable identity used for dedupe.
            ad_id = str(r.get("id", ""))
            url = r.get("redirect_url", "")
            if not url or not ad_id or ad_id in seen_ids:
                continue
            seen_ids.add(ad_id)
            jobs.append(Job(
                source="adzuna",
                company=(r.get("company") or {}).get("display_name", ""),
                title=r.get("title", "").replace("<strong>", "").replace("</strong>", ""),
                url=url,
                location=(r.get("location") or {}).get("display_name", ""),
                department=(r.get("category") or {}).get("label", ""),
                posted_at=r.get("created", ""),
                uid=ad_id,
            ))
    return jobs
