from .. import log
from ..http import post_json
from ..models import Job

PAGE_SIZE = 20
MAX_POSTINGS = 300


def fetch(cfg):
    jobs = []
    for board in cfg.get("boards", []):
        host, tenant, site = board["host"], board["tenant"], board["site"]
        api = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
        offset = 0
        try:
            while offset < MAX_POSTINGS:
                data = post_json(api, {
                    "appliedFacets": {},
                    "limit": PAGE_SIZE,
                    "offset": offset,
                    "searchText": board.get("search", "") or "",
                })
                postings = data.get("jobPostings", [])
                for p in postings:
                    path = p.get("externalPath", "")
                    if not path:
                        continue
                    jobs.append(Job(
                        source=f"workday:{tenant}",
                        company=tenant.title(),
                        title=p.get("title", ""),
                        url=f"https://{host}/en-US/{site}{path}",
                        location=p.get("locationsText", ""),
                        posted_at=p.get("postedOn", ""),
                    ))
                if len(postings) < PAGE_SIZE:
                    break
                offset += PAGE_SIZE
        except Exception as exc:
            log.warning("workday:%s failed: %s", tenant, exc)
    return jobs
