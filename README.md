# job-scout

24/7 watcher for **UK tech internships and 12-month placements** (security roles
flagged as priority). Runs free on GitHub Actions every 15 minutes and pings a
Discord webhook the moment a new matching posting appears.

## How it works

```
GitHub Actions (cron */15)
  └─ scraper/main.py
       ├─ sources: Greenhouse · Lever · Ashby · Workable · Workday APIs
       │           SimplifyJobs GitHub tracker · Adzuna API (UK aggregator)
       │           Gradcracker · RateMyPlacement (best-effort HTML)
       ├─ filters: intern/placement title + tech keyword + UK location
       │           security keywords → 🔐 priority alert
       ├─ state:   data/seen.json (committed back → no duplicate alerts)
       └─ notify:  Discord webhook embeds
```

Why no LinkedIn scraper? LinkedIn aggressively blocks bots and bans accounts.
Nearly every job posted there lives on the company's ATS (Greenhouse, Lever,
Workday…) — this project polls those APIs directly, which is more reliable and
usually *earlier* than the LinkedIn posting. Adzuna additionally aggregates
Reed, Totaljobs, CV-Library and other UK portals through an official API.

## Setup (~10 minutes)

1. **Discord webhook**: in your Discord server → channel → ⚙ Edit Channel →
   Integrations → Webhooks → New Webhook → Copy Webhook URL.

2. **Create a GitHub repo and push this folder** (public repo recommended —
   Actions minutes are unlimited for public repos; a private repo's 2000
   free min/month is NOT enough for a 15-minute cron):

   ```sh
   git init && git add -A && git commit -m "job-scout"
   gh repo create job-scout --public --source . --push
   ```

3. **Add secrets**: repo → Settings → Secrets and variables → Actions →
   New repository secret:
   - `DISCORD_WEBHOOK_URL` — required
   - `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` — optional but recommended; free key
     from <https://developer.adzuna.com> (covers many UK job portals)

4. **First run**: repo → Actions → "Job Scout" → Run workflow. The first run
   *seeds* the index silently (records existing postings without spamming you),
   then every later run alerts only on genuinely new postings.

5. **Validate sources** (recommended): Run workflow again with
   "Validate config source slugs" ticked. Remove any `FAIL` slugs from
   `config.yaml` — some seeded company slugs are educated guesses.

## Tuning

Everything lives in [`config.yaml`](config.yaml):

- **Add companies**: find the slug in the careers page URL —
  `boards.greenhouse.io/<slug>`, `jobs.lever.co/<slug>`,
  `jobs.ashbyhq.com/<slug>`, `apply.workable.com/<slug>`,
  `<tenant>.wdN.myworkdayjobs.com/<site>`. Add it under the matching source,
  then run the validate workflow.
- **Keywords**: `role_keywords` (must match), `exclude_keywords`,
  `tech_keywords`, `security_keywords` (priority flag), `uk_location_terms`.
- **Adzuna queries**: plain-English searches run against the whole UK market.

## Local usage

```sh
pip install -r requirements.txt
python -m scraper.selftest        # offline pipeline test
python -m scraper.main --dry-run  # full run, prints instead of posting
python -m scraper.validate        # check every configured slug
```

## Notes & limits

- GitHub cron isn't exact — expect alerts within ~15–30 min of a posting.
- Scheduled workflows pause after 60 days of repo inactivity; the state-commit
  each run counts as activity, so it stays alive on its own.
- Gradcracker/RateMyPlacement have no APIs; those scrapers are best-effort and
  fail gracefully if bot-blocked. The ATS + Adzuna sources are the reliable core.
- The same job found via two sources (e.g. Adzuna and Greenhouse) can alert
  twice — deduplication is per-source URL.
- Be a polite scraper: the default schedule is one lightweight request per
  source per 15 min. Don't crank it down to every minute.
