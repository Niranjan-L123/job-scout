import re


def _pattern(words):
    words = [w for w in (words or []) if str(w).strip()]
    if not words:
        return None
    parts = [r"\b" + re.escape(str(w).lower()) + r"\b" for w in words]
    return re.compile("|".join(parts))


class Classifier:
    def __init__(self, cfg):
        f = cfg["filters"]
        self.role = _pattern(f["role_keywords"])
        self.exclude = _pattern(f.get("exclude_keywords"))
        self.tech = _pattern(f.get("tech_keywords"))
        self.security = _pattern(f.get("security_keywords"))
        self.uk = _pattern(f.get("uk_location_terms"))
        self.require_tech = f.get("require_tech", True)
        self.allow_unknown_location = f.get("allow_unknown_location", True)

    def classify(self, job):
        """Return {"priority": bool} if the job matches, else None."""
        title = job.title.lower()
        title_dept = f"{job.title} {job.department}".lower()
        loc_title = f"{job.location} {job.title}".lower()

        if not self.role.search(title):
            return None
        if self.exclude and self.exclude.search(title):
            return None
        is_tech = bool(self.tech and self.tech.search(title_dept))
        is_security = bool(self.security and self.security.search(title_dept))
        if self.require_tech and self.tech and not (is_tech or is_security):
            return None
        if self.uk:
            if job.location.strip():
                if not self.uk.search(loc_title):
                    return None
            elif not self.allow_unknown_location:
                return None

        return {"priority": is_security}
