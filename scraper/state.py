import json
import os
import time


class State:
    def __init__(self, path):
        self.path = path
        self.data = {}
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    self.data = json.load(fh)
            except (json.JSONDecodeError, OSError):
                self.data = {}

    @property
    def is_empty(self):
        return not self.data

    def is_new(self, job):
        return job.key not in self.data

    def add(self, job):
        self.data[job.key] = {
            "first_seen": int(time.time()),
            "company": job.company,
            "title": job.title,
            "url": job.url,
        }

    def prune(self, max_age_days=180):
        cutoff = time.time() - max_age_days * 86400
        self.data = {
            k: v for k, v in self.data.items()
            if v.get("first_seen", 0) >= cutoff
        }

    def save(self):
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=1, sort_keys=True)
