"""Batch-prepare liked job URLs for tailoring (the deterministic half of
`/tailor-cv`).

For each URL it:
  1. ensures master.md is fresh (picks up any Word edits automatically),
  2. fetches a clean job description (scraper.jobpage),
  3. writes the JD + metadata into data/tailor/<slug>/,
  4. reports which URLs came back weak and need the user to paste the text.

It does NOT tailor or write any CV — that's Claude's job (resume-tailor skill),
working from the files this produces. Run:

    python -m tailor.prepare <url> [<url> ...]      # explicit URLs
    python -m tailor.prepare --shortlist            # read data/shortlist.txt

Prints a human report and a JSON block (between BEGIN_JSON/END_JSON) the
command can parse.
"""
import json
import re
import sys
from pathlib import Path

from scraper.jobpage import fetch_description

from . import SHORTLIST, master_sync

WORKDIR = Path(__file__).resolve().parent.parent / "data" / "tailor"
PROCESSED = WORKDIR / "processed.txt"


def slugify(text, fallback="job"):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or fallback


def _read_shortlist():
    if not SHORTLIST.exists():
        return []
    urls = []
    for line in SHORTLIST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line.split()[0])
    return urls


def _processed_urls():
    if not PROCESSED.exists():
        return set()
    return {l.strip() for l in PROCESSED.read_text(encoding="utf-8").splitlines() if l.strip()}


def prepare(urls):
    WORKDIR.mkdir(parents=True, exist_ok=True)
    changed, msg = master_sync.sync()
    done = _processed_urls()
    results = []

    for url in urls:
        if url in done:
            results.append({"url": url, "status": "skip", "reason": "already processed"})
            continue
        page = fetch_description(url)
        slug = slugify(page.company) + "-" + slugify(page.title)[:40] if page.company \
            else slugify(url.rsplit("/", 1)[-1] or url)
        slug = slug.strip("-") or "job"
        jobdir = WORKDIR / slug
        jobdir.mkdir(parents=True, exist_ok=True)
        (jobdir / "jd.txt").write_text(page.text, encoding="utf-8")
        meta = {
            "url": url,
            "status": "ok" if page.ok else "needs_paste",
            "company": page.company,
            "title": page.title,
            "kind": page.kind,
            "chars": page.chars,
            "reason": page.reason,
            "slug": slug,
            "jd_path": str((jobdir / "jd.txt").relative_to(WORKDIR.parent.parent)),
        }
        (jobdir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        results.append(meta)

    return {"master": msg, "master_changed": changed, "jobs": results}


def mark_processed(urls):
    WORKDIR.mkdir(parents=True, exist_ok=True)
    with PROCESSED.open("a", encoding="utf-8") as f:
        for u in urls:
            f.write(u + "\n")


def _report(summary):
    print(f"master: {summary['master']}\n")
    ok = [j for j in summary["jobs"] if j.get("status") == "ok"]
    paste = [j for j in summary["jobs"] if j.get("status") == "needs_paste"]
    skip = [j for j in summary["jobs"] if j.get("status") == "skip"]
    for j in ok:
        print(f"  OK          {j['company']} — {j['title']}  ({j['chars']} ch via {j['kind']})")
    for j in paste:
        print(f"  NEEDS PASTE {j.get('company') or j['url']}  ({j['reason']}) -> {j['url']}")
    for j in skip:
        print(f"  SKIP        {j['url']} ({j['reason']})")
    print(f"\n{len(ok)} ready, {len(paste)} need pasting, {len(skip)} skipped.")
    print("\nBEGIN_JSON")
    print(json.dumps(summary))
    print("END_JSON")


def main():
    # --mark <url>... : record URLs as processed (call after a successful batch).
    if "--mark" in sys.argv:
        urls = [a for a in sys.argv[1:] if a != "--mark"]
        mark_processed(urls)
        print(f"marked {len(urls)} URL(s) processed")
        return
    args = [a for a in sys.argv[1:] if a != "--shortlist"]
    if "--shortlist" in sys.argv or not args:
        args = _read_shortlist() or args
    if not args:
        print("usage: python -m tailor.prepare <url> [...] | --shortlist | --mark <url> ...")
        raise SystemExit(2)
    _report(prepare(args))


if __name__ == "__main__":
    main()
