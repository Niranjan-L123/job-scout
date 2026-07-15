import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-GB,en;q=0.9",
})


def get_json(url, **kwargs):
    r = SESSION.get(url, timeout=30, **kwargs)
    r.raise_for_status()
    return r.json()


def post_json(url, payload, **kwargs):
    r = SESSION.post(url, json=payload, timeout=30, **kwargs)
    r.raise_for_status()
    return r.json()


def get_html(url, **kwargs):
    r = SESSION.get(url, timeout=30, **kwargs)
    r.raise_for_status()
    return r.text
