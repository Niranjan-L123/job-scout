from .. import log
from ..http import get_json
from ..models import Job


def fetch(cfg):
    jobs = []
    for slug in cfg.get("companies", []):
        try:
            data = get_json(f"https://apply.workable.com/api/v1/widget/accounts/{slug}")
        except Exception as exc:
            log.warning("workable:%s failed: %s", slug, exc)
            continue
        company = data.get("name") or slug
        for j in data.get("jobs", []):
            url = j.get("url") or ""
            if not url and j.get("shortcode"):
                url = f"https://apply.workable.com/{slug}/j/{j['shortcode']}/"
            location = ", ".join(x for x in [j.get("city"), j.get("country")] if x)
            jobs.append(Job(
                source=f"workable:{slug}",
                company=company,
                title=j.get("title", ""),
                url=url,
                location=location,
                department=j.get("department") or "",
                posted_at=j.get("published_on") or "",
            ))
    return jobs
