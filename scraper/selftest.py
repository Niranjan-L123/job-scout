"""Offline self-test of the filtering, state and notification pipeline.

Usage: python -m scraper.selftest   (no network required)
"""
import os
import sys
import tempfile

from .config import load_config
from .filters import Classifier
from .models import Job
from .notify import send_matches
from .state import State

CASES = [
    # (job, should_match, should_be_priority)
    (Job("t", "Darktrace", "Cyber Security Industrial Placement", "https://x/1",
         "Cambridge, United Kingdom"), True, True),
    (Job("t", "Monzo", "Software Engineering Intern", "https://x/2",
         "London, UK"), True, False),
    (Job("t", "Arm", "Security Engineer Placement (12 Month)", "https://x/3",
         "Manchester"), True, True),
    (Job("t", "BigCo", "Software Engineer Intern", "https://x/4",
         "San Francisco, CA"), False, False),          # not UK
    (Job("t", "BigCo", "Senior Security Intern Programme Lead", "https://x/5",
         "London"), False, False),                     # excluded: senior
    (Job("t", "BigCo", "Marketing Placement Year", "https://x/6",
         "London"), False, False),                     # not tech
    (Job("t", "BigCo", "Internal Communications Executive", "https://x/7",
         "London"), False, False),                     # 'internal' is not 'intern'
    (Job("t", "Wayve", "Machine Learning Intern", "https://x/8",
         ""), True, False),                            # unknown location allowed
    (Job("t", "NCC", "Penetration Testing Year in Industry", "https://x/9",
         "Leeds, UK"), True, True),
]


def main():
    cfg = load_config(os.path.join(os.path.dirname(__file__), "..", "config.yaml"))
    clf = Classifier(cfg)
    failures = 0

    for job, want_match, want_priority in CASES:
        info = clf.classify(job)
        got_match = info is not None
        got_priority = bool(info and info["priority"])
        ok = got_match == want_match and (not want_match or got_priority == want_priority)
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"{status}  {job.title!r} -> match={got_match} priority={got_priority} "
              f"(want match={want_match} priority={want_priority})")

    # State round-trip
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "seen.json")
        st = State(path)
        assert st.is_empty
        job = CASES[0][0]
        assert st.is_new(job)
        st.add(job)
        st.save()
        st2 = State(path)
        assert not st2.is_new(job), "state did not persist"
        print("PASS  state persistence round-trip")

    # Notification formatting (dry run, prints to stdout)
    matches = [(j, {"priority": p}) for j, m, p in CASES if m]
    send_matches(matches, dry_run=True)
    print("PASS  notification dry-run")

    if failures:
        print(f"\n{failures} failure(s)")
        sys.exit(1)
    print("\nAll self-tests passed.")


if __name__ == "__main__":
    main()
