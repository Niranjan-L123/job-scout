"""Best-effort scraper for gradcracker.com placement search pages.

Gradcracker has no public API and may serve 403 to non-browser clients.
Failures are logged and skipped so the rest of the run continues.
"""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .. import log
from ..http import get_html
from ..models import Job

JOB_HREF = re.compile(r"/hubs/\d+", re.I)


def fetch(cfg):
    jobs = []
    for url in cfg.get("search_urls", []):
        try:
            html = get_html(url)
        except Exception as exc:
            log.warning("gradcracker %s failed: %s", url, exc)
            continue
        soup = BeautifulSoup(html, "html.parser")
        seen = set()
        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            title = a.get_text(" ", strip=True)
            if not JOB_HREF.search(href) or len(title) < 8 or href in seen:
                continue
            seen.add(href)
            # Company name is the slug segment after the hub id.
            m = re.search(r"/hubs/\d+/([^/]+)", href)
            company = m.group(1).replace("-", " ").title() if m else "Gradcracker"
            jobs.append(Job(
                source="gradcracker",
                company=company,
                title=title,
                url=href,
            ))
    return jobs
