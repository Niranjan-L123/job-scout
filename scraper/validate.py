"""Check that every configured company slug / board / URL actually responds.

Usage: python -m scraper.validate
Prints OK/FAIL per entry so you can prune bad slugs from config.yaml.
"""
import sys

from .config import load_config
from .sources import SOURCES

PER_COMPANY_SOURCES = ("greenhouse", "lever", "ashby", "workable")


def _check(label, fn):
    try:
        count = len(fn())
        print(f"  OK    {label} ({count} postings)")
        return True
    except Exception as exc:
        print(f"  FAIL  {label}: {exc}")
        return False


def main():
    cfg = load_config()
    failures = 0

    for name in PER_COMPANY_SOURCES:
        source_cfg = cfg["sources"].get(name) or {}
        module = SOURCES[name]
        print(f"{name}:")
        for slug in source_cfg.get("companies", []):
            if not _check(slug, lambda s=slug: module.fetch({"companies": [s]})):
                failures += 1

    workday_cfg = cfg["sources"].get("workday") or {}
    print("workday:")
    for board in workday_cfg.get("boards", []):
        module = SOURCES["workday"]
        if not _check(board["tenant"], lambda b=board: module.fetch({"boards": [b]})):
            failures += 1

    for name in ("simplify", "adzuna", "gradcracker", "ratemyplacement"):
        source_cfg = cfg["sources"].get(name) or {}
        print(f"{name}:")
        if not _check(name, lambda n=name, c=source_cfg: SOURCES[n].fetch(c)):
            failures += 1

    print(f"\n{failures} failure(s). Remove or fix failing entries in config.yaml.")
    sys.exit(0)


if __name__ == "__main__":
    main()
