"""Scraper for gradcracker.com placement/internship search pages.

Job links look like:
  /hub/<hubid>/<company-slug>/work-placement-internship/<jobid>/<title-slug>
Promotional webinar entries use the same pattern and are skipped.
"""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .. import log
from ..http import get_html
from ..models import Job

JOB_HREF = re.compile(
    r"/hub/\d+/([^/]+)/(?:work-placement-internship|graduate-job)/\d+/([^/?#]+)",
    re.I,
)


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
            m = JOB_HREF.search(href)
            if not m or href in seen or "gradcracker-webinar" in href:
                continue
            seen.add(href)
            company_slug, title_slug = m.group(1), m.group(2)
            title = a.get_text(" ", strip=True)
            if len(title) < 8:
                title = title_slug.replace("-", " ").title()
            jobs.append(Job(
                source="gradcracker",
                company=company_slug.replace("-", " ").title(),
                title=title,
                url=href,
                location="United Kingdom",
            ))
    return jobs
