from .. import log
from ..http import get_json
from ..models import Job


def fetch(cfg):
    jobs = []
    for slug in cfg.get("companies", []):
        try:
            data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
        except Exception as exc:
            log.warning("greenhouse:%s failed: %s", slug, exc)
            continue
        for j in data.get("jobs", []):
            jobs.append(Job(
                source=f"greenhouse:{slug}",
                company=j.get("company_name") or slug,
                title=j.get("title", ""),
                url=j.get("absolute_url", ""),
                location=(j.get("location") or {}).get("name", ""),
                posted_at=j.get("first_published") or j.get("updated_at") or "",
            ))
    return jobs
