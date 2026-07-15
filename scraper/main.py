import argparse
import sys

from . import log
from .config import load_config
from .filters import Classifier
from .notify import send_matches, send_text
from .sources import SOURCES
from .state import State


def collect_jobs(cfg):
    all_jobs = []
    for name, source_cfg in cfg.get("sources", {}).items():
        if not (source_cfg or {}).get("enabled", True):
            continue
        module = SOURCES.get(name)
        if module is None:
            log.warning("unknown source %r in config, skipping", name)
            continue
        try:
            jobs = module.fetch(source_cfg)
        except Exception as exc:
            log.warning("source %s failed: %s", name, exc)
            continue
        log.info("%s: %d postings", name, len(jobs))
        all_jobs.extend(jobs)
    return all_jobs


def run(dry_run=False, config_path=None):
    cfg = load_config(config_path)
    classifier = Classifier(cfg)
    state = State(cfg.get("state_path", "data/seen.json"))
    seeding = state.is_empty

    all_jobs = collect_jobs(cfg)

    matched = 0
    new_matches = []
    for job in all_jobs:
        if not job.title or not job.url:
            continue
        info = classifier.classify(job)
        if info is None:
            continue
        matched += 1
        if state.is_new(job):
            state.add(job)
            new_matches.append((job, info))

    state.prune()
    state.save()

    if seeding:
        # First ever run: index everything silently so the user isn't
        # flooded with hundreds of "new" postings that already existed.
        send_text(
            f"\U0001F331 job-scout initialised: indexed {matched} existing matching "
            f"posting(s) across {len(all_jobs)} scanned jobs. "
            "From now on you'll be pinged the moment a new one appears.",
            dry_run,
        )
    elif new_matches:
        send_matches(new_matches, dry_run)

    log.info("scanned=%d matched=%d new=%d seeding=%s",
             len(all_jobs), matched, len(new_matches), seeding)
    return 0


def main():
    parser = argparse.ArgumentParser(prog="job-scout")
    parser.add_argument("--dry-run", action="store_true",
                        help="print matches instead of posting to Discord")
    parser.add_argument("--config", default=None, help="path to config.yaml")
    args = parser.parse_args()
    sys.exit(run(dry_run=args.dry_run, config_path=args.config))


if __name__ == "__main__":
    main()
