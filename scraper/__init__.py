import logging
import sys

# Windows consoles default to cp1252, which can't print the emoji used in
# notifications; force UTF-8 with replacement so output never crashes a run.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("job-scout")
