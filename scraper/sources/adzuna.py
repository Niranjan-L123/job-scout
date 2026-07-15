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

    jobs, seen_urls = [], set()
    for query in cfg.get("queries", []):
        try:
            data = get_json(API, params={
                "app_id": app_id,
                "app_key": app_key,
                "what": query,
                "results_per_page": 50,
                "max_days_old": cfg.get("max_days_old", 3),
                "sort_by": "date",
            })
        except Exception as exc:
            log.warning("adzuna query %r failed: %s", query, exc)
            continue
        for r in data.get("results", []):
            url = r.get("redirect_url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            jobs.append(Job(
                source="adzuna",
                company=(r.get("company") or {}).get("display_name", ""),
                title=r.get("title", "").replace("<strong>", "").replace("</strong>", ""),
                url=url,
                location=(r.get("location") or {}).get("display_name", ""),
                department=(r.get("category") or {}).get("label", ""),
                posted_at=r.get("created", ""),
            ))
    return jobs
