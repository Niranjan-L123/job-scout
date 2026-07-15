import logging
import sys

try:
    # Use the OS certificate store when available; needed on machines where
    # TLS is intercepted by a proxy/AV whose root cert isn't in certifi.
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

# Windows consoles default to cp1252, which can't print the emoji used in
# notifications; force UTF-8 with replacement so output never crashes a run.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("job-scout")
