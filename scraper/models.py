import hashlib
from dataclasses import dataclass


@dataclass
class Job:
    source: str
    company: str
    title: str
    url: str
    location: str = ""
    department: str = ""
    posted_at: str = ""

    @property
    def key(self) -> str:
        return hashlib.sha1(f"{self.source}|{self.url}".encode()).hexdigest()
