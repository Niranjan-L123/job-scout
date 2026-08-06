"""Minimal, formatting-preserving docx text editing.

The tailored CV is produced by CLONING the polished single-page template and
replacing text *inside its existing paragraph structure* — never rebuilding the
layout — so the hand-tuned one-page formatting (margins, tables, fonts) is kept
exactly.

Editing is done with string surgery on the raw document.xml, NOT via an XML
library: round-tripping OOXML through ElementTree mangles namespace prefixes
(w14:, r:, mc: ...) and Word then reports the file as corrupt. We only touch the
`<w:t>` runs of paragraphs we change; every other byte is preserved verbatim.

Word splits a paragraph's text across several runs, so replacement works at the
paragraph level: concatenate a paragraph's run text, and if a target is found,
write the replacement into the first run and blank the rest (keeping the first
run's formatting).

    from tailor.docx_edit import Docx
    d = Docx.clone(TEMPLATE_DOCX)
    d.paragraphs()                       # inspect current text, in order
    d.replace_map({"old phrase": "new"})
    d.save(out_path)
"""
import html
import re
import shutil
import zipfile
from pathlib import Path

_P_RE = re.compile(r"<w:p\b.*?</w:p>", re.S)          # w:p never nests
_T_RE = re.compile(r"(<w:t\b[^>]*>)(.*?)(</w:t>)", re.S)


class Docx:
    def __init__(self, path):
        self.path = Path(path)
        with zipfile.ZipFile(self.path) as z:
            self._names = z.namelist()
            self._blobs = {n: z.read(n) for n in self._names}
        self.xml = self._blobs["word/document.xml"].decode("utf-8")

    @classmethod
    def clone(cls, template, dest=None):
        """Return a Docx backed by a copy of `template` (optionally at dest)."""
        if dest:
            Path(dest).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(template, dest)
            return cls(dest)
        return cls(template)

    @staticmethod
    def _para_text(p_xml):
        return html.unescape("".join(m.group(2) for m in _T_RE.finditer(p_xml)))

    def paragraphs(self):
        return [t for t in (self._para_text(p) for p in _P_RE.findall(self.xml))
                if t.strip()]

    def replace_map(self, mapping):
        """Apply {old_substring: new_string} across paragraphs. Longest keys
        first so specific phrases win. Returns the number of paragraphs changed."""
        keys = sorted((k for k in mapping if k), key=len, reverse=True)
        changed = 0

        def _sub_para(pm):
            nonlocal changed
            p = pm.group(0)
            text = self._para_text(p)
            if not text.strip():
                return p
            new = text
            for k in keys:
                if k in new:
                    new = new.replace(k, mapping[k])
            if new == text:
                return p
            changed += 1
            return self._write_para_text(p, new)

        self.xml = _P_RE.sub(_sub_para, self.xml)
        return changed

    def _sole_para_in_cell(self, start, end):
        """True if the paragraph at [start:end] is the only <w:p> in its table
        cell — such a paragraph must not be removed (an empty <w:tc> is invalid
        OOXML and Word reports the file as corrupt)."""
        tc_open = self.xml.rfind("<w:tc>", 0, start)
        tc_close = self.xml.find("</w:tc>", end)
        if tc_open == -1 or tc_close == -1:
            return False
        if "</w:tc>" in self.xml[tc_open:start]:
            return False  # nearest cell already closed -> paragraph isn't in one
        return len(_P_RE.findall(self.xml[tc_open:tc_close])) == 1

    def delete_paragraphs(self, substrings):
        """Trim paragraphs whose text contains any of `substrings`, reclaiming
        the line. Standalone paragraphs are removed outright; a paragraph that
        is the sole one in a table cell is blanked instead (safe). Returns the
        number of paragraphs removed (not counting blanked ones)."""
        subs = [s for s in substrings if s]
        if not subs:
            return 0
        removed = 0
        out, last = [], 0
        for m in _P_RE.finditer(self.xml):
            p = m.group(0)
            text = self._para_text(p)
            if text.strip() and any(s in text for s in subs):
                out.append(self.xml[last:m.start()])
                if self._sole_para_in_cell(m.start(), m.end()):
                    out.append(self._write_para_text(p, ""))  # keep cell valid
                else:
                    removed += 1                                # drop entirely
                last = m.end()
        out.append(self.xml[last:])
        self.xml = "".join(out)
        return removed

    @staticmethod
    def _write_para_text(p_xml, new_text):
        """Put new_text into the paragraph's first run, blank the others."""
        runs = list(_T_RE.finditer(p_xml))
        if not runs:
            return p_xml
        escaped = html.escape(new_text, quote=False)
        out, last = [], 0
        for i, m in enumerate(runs):
            out.append(p_xml[last:m.start()])
            if i == 0:
                open_tag = m.group(1)
                if "xml:space" not in open_tag:
                    open_tag = open_tag[:-1] + ' xml:space="preserve">'
                out.append(open_tag + escaped + m.group(3))
            else:
                out.append(m.group(1) + m.group(3))  # empty this run
            last = m.end()
        out.append(p_xml[last:])
        return "".join(out)

    def save(self, out_path):
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self._blobs["word/document.xml"] = self.xml.encode("utf-8")
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
            for n in self._names:
                z.writestr(n, self._blobs[n])
        return out_path
