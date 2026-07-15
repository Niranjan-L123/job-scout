from .. import log
from ..http import get_json
from ..models import Job


def fetch(cfg):
    jobs = []
    for slug in cfg.get("companies", []):
        try:
            data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
        except Exception as exc:
            log.warning("ashby:%s failed: %s", slug, exc)
            continue
        for j in data.get("jobs", []):
            if j.get("isListed") is False:
                continue
            locs = [j.get("location") or ""]
            locs += [s.get("location", "") for s in j.get("secondaryLocations") or []]
            jobs.append(Job(
                source=f"ashby:{slug}",
                company=slug.replace("-", " ").title(),
                title=j.get("title", ""),
                url=j.get("jobUrl") or j.get("applyUrl") or "",
                location=", ".join(x for x in locs if x),
                department=j.get("department") or "",
                posted_at=j.get("publishedAt") or "",
            ))
    return jobs
