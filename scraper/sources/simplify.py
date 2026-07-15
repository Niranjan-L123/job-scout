from .. import log
from ..http import get_json
from ..models import Job

DEFAULT_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships"
    "/dev/.github/scripts/listings.json"
)


def fetch(cfg):
    jobs = []
    for url in cfg.get("listing_urls", [DEFAULT_URL]):
        try:
            data = get_json(url)
        except Exception as exc:
            log.warning("simplify tracker %s failed: %s", url, exc)
            continue
        for e in data:
            if not e.get("active", True) or not e.get("is_visible", True):
                continue
            jobs.append(Job(
                source="simplify",
                company=e.get("company_name", ""),
                title=e.get("title", ""),
                url=e.get("url", ""),
                location=", ".join(e.get("locations") or []),
                posted_at=str(e.get("date_posted", "")),
            ))
    return jobs
