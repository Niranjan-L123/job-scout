"""Best-effort scraper for ratemyplacement.co.uk search pages.

No public API; may be bot-blocked. Failures are logged and skipped.
"""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .. import log
from ..http import get_html
from ..models import Job

JOB_HREF = re.compile(r"/jobs?/\d+", re.I)


def fetch(cfg):
    jobs = []
    for url in cfg.get("search_urls", []):
        try:
            html = get_html(url)
        except Exception as exc:
            log.warning("ratemyplacement %s failed: %s", url, exc)
            continue
        soup = BeautifulSoup(html, "html.parser")
        seen = set()
        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            title = a.get_text(" ", strip=True)
            if not JOB_HREF.search(href) or len(title) < 8 or href in seen:
                continue
            seen.add(href)
            jobs.append(Job(
                source="ratemyplacement",
                company="RateMyPlacement listing",
                title=title,
                url=href,
            ))
    return jobs
