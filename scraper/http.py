import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# Per-request cap. Kept tight so a single degraded host can't stall the whole
# run toward the workflow's 15-minute timeout.
DEFAULT_TIMEOUT = 15

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-GB,en;q=0.9",
})


def get_json(url, **kwargs):
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    r = SESSION.get(url, **kwargs)
    r.raise_for_status()
    return r.json()


def post_json(url, payload, **kwargs):
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    r = SESSION.post(url, json=payload, **kwargs)
    r.raise_for_status()
    return r.json()


def get_html(url, **kwargs):
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    r = SESSION.get(url, **kwargs)
    r.raise_for_status()
    return r.text
