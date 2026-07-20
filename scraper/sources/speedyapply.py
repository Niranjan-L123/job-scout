"""Parser for the speedyapply/2026-SWE-College-Jobs markdown tables.

Rows look like: | [Company](url) | Role | Location | Age | <a href="apply"><img/></a> |
Cell order can drift, so parsing is defensive: first link-ish cell is the
company, the last http link in the row is the apply URL.
"""
import re

from .. import log
from ..http import SESSION
from ..models import Job

DEFAULT_URLS = [
    "https://raw.githubusercontent.com/speedyapply/2026-SWE-College-Jobs/main/INTERN_INTL.md",
]

MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
HREF = re.compile(r'href="(https?://[^"]+)"')
TAGS = re.compile(r"<[^>]+>|\*\*|\*")


def _clean(cell):
    return TAGS.sub("", MD_LINK.sub(r"\1", cell)).strip()


def fetch(cfg):
    jobs = []
    for url in cfg.get("listing_urls", DEFAULT_URLS):
        try:
            r = SESSION.get(url, timeout=30)
            r.raise_for_status()
        except Exception as exc:
            log.warning("speedyapply %s failed: %s", url, exc)
            continue
        for line in r.text.splitlines():
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 3 or set(cells[0]) <= {"-", " ", ":"}:
                continue  # separator or malformed row
            company = _clean(cells[0])
            title = _clean(cells[1])
            location = _clean(cells[2]) if len(cells) > 2 else ""
            links = HREF.findall(line) + [m[1] for m in MD_LINK.findall(line)]
            apply_links = [u for u in links if "github.com" not in u]
            if not apply_links or not company or not title:
                continue
            jobs.append(Job(
                source="speedyapply",
                company=company,
                title=title,
                url=apply_links[-1],
                location=location,
            ))
    return jobs
