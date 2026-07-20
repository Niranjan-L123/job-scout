import hashlib
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Query params that change between requests (tracking tokens) and must not
# influence a job's identity.
TRACKING_PARAMS = ("utm_", "se", "v", "ref", "gh_src", "lever-source")


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    query = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not (k in TRACKING_PARAMS or any(k.startswith(p) for p in ("utm_",)))
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path,
                       urlencode(query), ""))


@dataclass
class Job:
    source: str
    company: str
    title: str
    url: str
    location: str = ""
    department: str = ""
    posted_at: str = ""
    uid: str = ""  # stable provider id; preferred over url for dedupe

    @property
    def key(self) -> str:
        ident = self.uid or canonical_url(self.url)
        return hashlib.sha1(f"{self.source}|{ident}".encode()).hexdigest()
