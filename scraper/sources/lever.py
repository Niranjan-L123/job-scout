from .. import log
from ..http import get_json
from ..models import Job


def fetch(cfg):
    jobs = []
    for slug in cfg.get("companies", []):
        try:
            data = get_json(f"https://api.lever.co/v0/postings/{slug}?mode=json")
        except Exception as exc:
            log.warning("lever:%s failed: %s", slug, exc)
            continue
        for j in data:
            cats = j.get("categories") or {}
            dept = " / ".join(x for x in [cats.get("team"), cats.get("commitment")] if x)
            jobs.append(Job(
                source=f"lever:{slug}",
                company=slug.replace("-", " ").title(),
                title=j.get("text", ""),
                url=j.get("hostedUrl", ""),
                location=cats.get("location") or "",
                department=dept,
                posted_at=str(j.get("createdAt", "")),
            ))
    return jobs
