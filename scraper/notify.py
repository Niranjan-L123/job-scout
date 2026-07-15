import os
import time

import requests

from . import log

COLOR_SECURITY = 0xE74C3C
COLOR_NORMAL = 0x2ECC71


def _embed(job, priority):
    lines = []
    if job.location:
        lines.append(f"\U0001F4CD {job.location}")
    if job.department:
        lines.append(f"\U0001F3F7 {job.department}")
    lines.append(f"\U0001F50E via {job.source}")
    return {
        "title": ("\U0001F510 " if priority else "\U0001F4BC ") + job.title[:240],
        "url": job.url,
        "description": "\n".join(lines)[:2000],
        "author": {"name": job.company[:240] or "Unknown company"},
        "color": COLOR_SECURITY if priority else COLOR_NORMAL,
    }


def _post(webhook, payload):
    resp = requests.post(webhook, json=payload, timeout=30)
    if resp.status_code == 429:
        retry = 2.0
        try:
            retry = float(resp.json().get("retry_after", 2))
        except Exception:
            pass
        time.sleep(retry + 0.5)
        resp = requests.post(webhook, json=payload, timeout=30)
    if resp.status_code >= 400:
        log.warning("Discord webhook returned %s: %s", resp.status_code, resp.text[:300])


def send_matches(matches, dry_run=False):
    """matches: list of (Job, {"priority": bool}) tuples."""
    webhook = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if dry_run or not webhook:
        for job, info in matches:
            tag = "PRIORITY/SECURITY" if info["priority"] else "match"
            print(f"[{tag}] {job.company} | {job.title} | {job.location} | {job.url}")
        if not webhook and not dry_run:
            log.warning("DISCORD_WEBHOOK_URL not set; matches printed to stdout only.")
        return

    # Security roles first, 10 embeds per Discord message.
    ordered = sorted(matches, key=lambda m: not m[1]["priority"])
    for i in range(0, len(ordered), 10):
        chunk = ordered[i:i + 10]
        payload = {"embeds": [_embed(j, info["priority"]) for j, info in chunk]}
        if i == 0:
            payload["content"] = f"**{len(ordered)} new posting(s) found**"
        _post(webhook, payload)
        time.sleep(1)


def send_text(message, dry_run=False):
    webhook = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if dry_run or not webhook:
        print(message)
        return
    _post(webhook, {"content": message})
