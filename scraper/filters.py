import re

# A trailing US state / Canadian province code (", CA", ", MA", ", BC") is a
# strong non-UK signal. Matched case-sensitively against the raw location so it
# doesn't catch lowercase words.
_US_STATES = (
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO "
    "MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY "
    "DC BC ON QC AB").split()
US_STATE = re.compile(r",\s*(?:" + "|".join(_US_STATES) + r")\b")

# Unambiguous UK markers. If one of these is present, a non-UK signal elsewhere
# in a multi-location string (e.g. "London, UK, SF, NYC") is tolerated.
STRONG_UK = re.compile(
    r"\b(?:united kingdom|uk|gb|england|scotland|wales|northern ireland)\b")


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
        self.spam = _pattern(f.get("spam_keywords"))
        self.tech = _pattern(f.get("tech_keywords"))
        self.security = _pattern(f.get("security_keywords"))
        self.uk = _pattern(f.get("uk_location_terms"))
        self.exclude_loc = _pattern(f.get("exclude_location_terms"))
        self.require_tech = f.get("require_tech", True)
        self.allow_unknown_location = f.get("allow_unknown_location", True)
        # Sources that are US/international by default: only let a posting
        # through with a positive UK location (no unknown-location benefit).
        self.strict_sources = set(f.get("strict_location_sources", []))

    def classify(self, job):
        """Return {"priority": bool} if the job matches, else None."""
        title = job.title.lower()
        title_dept = f"{job.title} {job.department}".lower()
        loc_title = f"{job.location} {job.title}".lower()

        if not self.role.search(title):
            return None
        if self.exclude and self.exclude.search(title):
            return None
        # Reject self-funded training-course "jobs" — the tell is often in the
        # company name (course sellers) or department, not just the title.
        if self.spam and self.spam.search(
                f"{job.title} {job.company} {job.department}".lower()):
            return None
        is_tech = bool(self.tech and self.tech.search(title_dept))
        is_security = bool(self.security and self.security.search(title_dept))
        if self.require_tech and self.tech and not (is_tech or is_security):
            return None
        # --- Location: reject non-UK, keep genuine UK (incl. collision cities
        # like Cambridge MA vs Cambridge UK, disambiguated by state code). ---
        loc_l = job.location.lower()
        nonuk = bool((self.exclude_loc and self.exclude_loc.search(loc_l))
                     or US_STATE.search(job.location))
        strong_uk = bool(STRONG_UK.search(loc_l))
        if nonuk and not strong_uk:
            return None
        if job.location.strip():
            if self.uk and not self.uk.search(loc_title):
                return None
        elif job.source in self.strict_sources or not self.allow_unknown_location:
            return None

        return {"priority": is_security}
