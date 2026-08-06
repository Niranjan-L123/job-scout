"""Fetch a clean, readable job description for a single posting URL.

Used by the resume-tailoring workflow: given a URL the user liked (usually
pasted from a Discord alert), return the description text so the resume-tailor
skill can work from it without the user copy-pasting anything.

Design notes:
- The ATS boards we already scrape (Greenhouse, Lever, Workable, Workday) expose
  a clean per-posting JSON API, so we parse those directly.
- Everything else (Ashby, Adzuna redirect targets, Gradcracker, unknown boards)
  falls back to generic HTML readability.
- Every result carries a quality verdict. If we could NOT get a real description
  (JS-walled page, cookie/nav shell, redirect we couldn't follow), `ok` is False
  and the caller is expected to ask the user to paste the description instead of
  tailoring from junk.

Standalone use:
    python -m scraper.jobpage <url>
"""
import html
import json
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from . import log
from .http import SESSION

# Text shorter than this almost certainly isn't a real description.
MIN_CHARS = 320
# Above this length we accept it even without obvious signal words.
STRONG_CHARS = 900
# Phrases a genuine job description almost always contains.
SIGNAL_WORDS = (
    "responsibilit", "require", "qualif", "experience", "skills", "you will",
    "you'll", "the role", "about the", "we are looking", "who you are",
    "what you", "degree", "benefits", "team", "apply", "opportunit",
)


@dataclass
class JobPage:
    url: str
    ok: bool
    text: str = ""
    kind: str = ""       # which extractor produced this (greenhouse, generic, ...)
    chars: int = 0
    reason: str = ""     # why ok is False, for the user-facing message
    title: str = ""      # parsed job title, when available
    company: str = ""    # parsed hiring company, when available

    def __bool__(self):
        return self.ok


# --------------------------------------------------------------------------- #
# HTML -> text
# --------------------------------------------------------------------------- #
_BLOCK_TAGS = ("p", "li", "br", "div", "h1", "h2", "h3", "h4", "tr", "ul", "ol")


def html_to_text(markup: str) -> str:
    """Strip tags to readable plain text, preserving paragraph/line breaks."""
    if not markup:
        return ""
    # Some APIs return HTML entity-encoded markup (e.g. Greenhouse `content`).
    if "<" not in markup and "&lt;" in markup:
        markup = html.unescape(markup)
    soup = BeautifulSoup(markup, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "header",
                     "footer", "form", "button"]):
        tag.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for tag in soup.find_all(["p", "li", "div", "h1", "h2", "h3", "h4", "tr"]):
        tag.append("\n")
    text = soup.get_text()
    text = html.unescape(text)
    # Collapse runs of whitespace but keep line structure.
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines).strip()


def _verdict(text, kind, title="", company=""):
    text = (text or "").strip()
    n = len(text)
    if n >= STRONG_CHARS:
        return JobPage("", True, text, kind, n, title=title, company=company)
    low = text.lower()
    if n >= MIN_CHARS and any(w in low for w in SIGNAL_WORDS):
        return JobPage("", True, text, kind, n, title=title, company=company)
    return JobPage("", False, text, kind, n,
                   reason=f"only {n} chars of usable text extracted",
                   title=title, company=company)


# --------------------------------------------------------------------------- #
# Per-ATS extractors (clean JSON APIs)
# --------------------------------------------------------------------------- #
def _greenhouse(parts):
    # boards.greenhouse.io/<slug>/jobs/<id>  or job-boards.greenhouse.io/...
    m = re.search(r"/([^/]+)/jobs/(\d+)", parts.path)
    if not m:
        m = re.search(r"[?&]gh_jid=(\d+)", parts.query)  # embedded widget
        return None if not m else None  # slug unknown -> let generic try
    slug, jid = m.group(1), m.group(2)
    api = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{jid}?questions=false"
    data = SESSION.get(api, timeout=30).json()
    title = data.get("title", "")
    body = html_to_text(data.get("content", ""))
    company = data.get("company_name") or slug.replace("-", " ").title()
    return _verdict(f"{title}\n\n{body}".strip(), "greenhouse", title, company)


def _lever(parts):
    m = re.search(r"/([^/]+)/([0-9a-f-]{16,})", parts.path)
    if not m:
        return None
    slug, pid = m.group(1), m.group(2)
    api = f"https://api.lever.co/v0/postings/{slug}/{pid}?mode=json"
    data = SESSION.get(api, timeout=30).json()
    chunks = [data.get("text", ""), html_to_text(data.get("description", ""))]
    for lst in data.get("lists", []) or []:
        chunks.append(html_to_text(lst.get("text", "")))
        chunks.append(html_to_text(lst.get("content", "")))
    chunks.append(html_to_text(data.get("additional", "")))
    return _verdict("\n\n".join(c for c in chunks if c), "lever",
                    data.get("text", ""), slug.replace("-", " ").title())


def _workable(parts):
    m = re.search(r"/([^/]+)/j/([^/]+)", parts.path)
    if not m:
        # Short form apply.workable.com/j/<code> -> follow redirect for the slug.
        code = re.search(r"/j/([^/?]+)", parts.path)
        if not code:
            return None
        final = SESSION.get(f"https://{parts.netloc}{parts.path}", timeout=30).url
        m = re.search(r"/([^/]+)/j/([^/?]+)", final)
        if not m:
            return None
    slug, shortcode = m.group(1), m.group(2)
    api = f"https://apply.workable.com/api/v3/accounts/{slug}/jobs/{shortcode}"
    data = SESSION.get(api, timeout=30).json()
    parts_ = [
        data.get("title", ""),
        html_to_text(data.get("description", "")),
        html_to_text(data.get("requirements", "")),
        html_to_text(data.get("benefits", "")),
    ]
    return _verdict("\n\n".join(p for p in parts_ if p), "workable",
                    data.get("title", ""), slug.replace("-", " ").title())


def _workday(parts):
    # https://<tenant>.wdN.myworkdayjobs.com/<locale?>/<site>/job/<path...>
    host = parts.netloc
    tenant = host.split(".")[0]
    segs = [s for s in parts.path.split("/") if s]
    if "job" not in segs:
        return None
    ji = segs.index("job")
    # site is the segment before 'job', skipping a leading locale like en-US.
    site = segs[ji - 1] if ji >= 1 else ""
    job_path = "/".join(segs[ji:])  # job/<location>/<slug>
    api = f"https://{host}/wday/cxs/{tenant}/{site}/{job_path}"
    data = SESSION.get(api, timeout=30, headers={"Accept": "application/json"}).json()
    info = data.get("jobPostingInfo") or {}
    title = info.get("title", "")
    body = html_to_text(info.get("jobDescription", ""))
    return _verdict(f"{title}\n\n{body}".strip(), "workday",
                    title, tenant.replace("-", " ").title())


# --------------------------------------------------------------------------- #
# Generic HTML readability fallback
# --------------------------------------------------------------------------- #
def _jsonld_jobposting(soup):
    """Many boards embed a schema.org JobPosting in a <script ld+json> tag."""
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text() or ""
        try:
            data = json.loads(raw)
        except Exception:
            continue
        for obj in (data if isinstance(data, list) else [data]):
            graph = obj.get("@graph", [obj]) if isinstance(obj, dict) else [obj]
            for node in graph:
                if not isinstance(node, dict):
                    continue
                types = node.get("@type", "")
                types = types if isinstance(types, list) else [types]
                if "JobPosting" in types and node.get("description"):
                    title = node.get("title", "")
                    org = node.get("hiringOrganization") or {}
                    company = org.get("name", "") if isinstance(org, dict) else ""
                    body = html_to_text(node["description"])
                    return f"{title}\n\n{body}".strip(), title, company
    return "", "", ""


def _generic(url):
    r = SESSION.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Preferred: a structured JobPosting blob (clean, complete).
    ld_text, ld_title, ld_company = _jsonld_jobposting(soup)
    if ld_text:
        v = _verdict(ld_text, "jsonld", ld_title, ld_company)
        if v.ok:
            return v

    for tag in soup(["script", "style", "noscript", "svg", "nav", "header",
                     "footer", "form", "button", "aside"]):
        tag.decompose()
    # Prefer an explicit main/article container; else the densest block.
    candidates = soup.select("main, article, [role=main], .job, #job, .content")
    node = None
    best = 0
    for c in candidates or soup.find_all(["section", "div"]):
        length = len(c.get_text(strip=True))
        if length > best:
            best, node = length, c
    node = node or soup.body or soup
    return _verdict(html_to_text(str(node)), "generic")


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
_ROUTES = (
    ("greenhouse.io", _greenhouse),
    ("lever.co", _lever),
    ("workable.com", _workable),
    ("myworkdayjobs.com", _workday),
)


def fetch_description(url: str) -> JobPage:
    """Return a JobPage for `url`. `ok` is False when the caller should ask the
    user to paste the description instead of trusting what we extracted."""
    url = (url or "").strip()
    if not url:
        return JobPage(url, False, reason="empty URL")
    parts = urlsplit(url)
    host = parts.netloc.lower()

    result = None
    for needle, fn in _ROUTES:
        if needle in host:
            try:
                result = fn(parts)
            except Exception as exc:
                log.warning("jobpage %s (%s) API failed: %s", url, needle, exc)
                result = None
            break

    # Fall back to generic readability if no ATS route matched or the API
    # route returned nothing / weak text.
    if result is None or not result.ok:
        try:
            generic = _generic(url)
        except Exception as exc:
            if result is not None:
                result.url = url
                return result
            return JobPage(url, False, reason=f"could not fetch page: {exc}")
        # Keep whichever gave a real description; prefer the ATS one if valid.
        result = result if (result and result.ok) else generic

    result.url = url
    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("usage: python -m scraper.jobpage <url>")
        raise SystemExit(2)
    page = fetch_description(sys.argv[1])
    status = "OK" if page.ok else f"NEEDS-PASTE ({page.reason})"
    print(f"[{status}] kind={page.kind} chars={page.chars}\n")
    print(page.text[:4000])
