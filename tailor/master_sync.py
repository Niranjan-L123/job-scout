"""Keep master.md in sync with the master CV .docx.

The .docx stays the single thing the user edits (in Word). master.md is a
derived, readable mirror the tailoring workflow reads from. We regenerate it
only when the .docx has been modified more recently, so an edit in Word is
picked up automatically on the next tailor run — the user never hand-syncs.

Usage:
    python -m tailor.master_sync          # sync if stale, report what happened
    python -m tailor.master_sync --force  # always regenerate
"""
import sys
import zipfile
from xml.etree import ElementTree as ET

from . import MASTER_DOCX, MASTER_MD

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _paragraphs(docx_path):
    """Yield the visible text of each paragraph, in document order."""
    with zipfile.ZipFile(docx_path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    for p in root.iter(f"{W}p"):
        text = "".join(t.text for t in p.iter(f"{W}t") if t.text)
        yield text.strip()


def _is_section_header(line):
    # e.g. EDUCATION, PROJECTS, SKILLS & INTERESTS — upper-case, short, no digits.
    letters = [c for c in line if c.isalpha()]
    return bool(letters) and line.upper() == line and len(line) <= 30 \
        and not any(c.isdigit() for c in line)


def to_markdown(docx_path):
    lines = [ln for ln in _paragraphs(docx_path)]
    out = []
    seen_name = False
    for ln in lines:
        if not ln:
            continue
        if not seen_name:
            out.append(f"# {ln}")       # first non-empty line = name
            seen_name = True
        elif _is_section_header(ln):
            out.append("")
            out.append(f"## {ln}")
        else:
            out.append(ln)
    return "\n".join(out).strip() + "\n"


def sync(force=False):
    """Regenerate master.md if the docx is newer (or missing/forced).
    Returns (changed: bool, message: str)."""
    if not MASTER_DOCX.exists():
        return False, f"master docx not found: {MASTER_DOCX}"
    fresh = MASTER_MD.exists() and \
        MASTER_MD.stat().st_mtime >= MASTER_DOCX.stat().st_mtime
    if fresh and not force:
        return False, f"master.md already up to date ({MASTER_MD})"
    MASTER_MD.write_text(to_markdown(MASTER_DOCX), encoding="utf-8")
    return True, f"regenerated {MASTER_MD} from {MASTER_DOCX.name}"


def main():
    changed, msg = sync(force="--force" in sys.argv)
    print(("[synced] " if changed else "[skip]  ") + msg)


if __name__ == "__main__":
    main()
