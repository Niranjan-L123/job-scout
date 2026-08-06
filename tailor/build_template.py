"""Build the tailoring template: the polished Verkada 1-page layout plus a
PROFILE section slot at the top.

The profile is a single justified body line seeded with PROFILE_PLACEHOLDER,
which /tailor-cv replaces per job with an ATS-keyword-rich summary. We insert
raw OOXML (matching the existing heading/body run properties) right before the
EDUCATION heading, then rewrite the docx zip — styles/theme/tables untouched.

Run once (or after the Verkada CV's layout changes):
    python -m tailor.build_template
"""
import zipfile

from . import PROFILE_PLACEHOLDER, RESUME_ROOT, TEMPLATE_DOCX

SOURCE = RESUME_ROOT / "verkada" / "Niranjan_Lakshminarasimhan_CV.docx"

# Heading run properties: bold + single underline, Times New Roman 10.5pt.
_RPR_HEAD = ('<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"'
             ' w:cs="Times New Roman"/><w:b/><w:bCs/><w:sz w:val="21"/>'
             '<w:szCs w:val="21"/><w:u w:val="single"/></w:rPr>')
# Body run properties: Times New Roman 10.5pt, regular.
_RPR_BODY = ('<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"'
             ' w:cs="Times New Roman"/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr>')

PROFILE_HEADING = (
    f'<w:p><w:pPr><w:spacing w:before="20" w:after="6"/>{_RPR_HEAD}</w:pPr>'
    f'<w:r>{_RPR_HEAD}<w:t>PROFILE</w:t></w:r></w:p>'
)
PROFILE_BODY = (
    f'<w:p><w:pPr><w:spacing w:before="0" w:after="6" w:line="216" '
    f'w:lineRule="auto"/><w:jc w:val="both"/>{_RPR_BODY}</w:pPr>'
    f'<w:r>{_RPR_BODY}<w:t xml:space="preserve">{PROFILE_PLACEHOLDER}</w:t>'
    f'</w:r></w:p>'
)


def build():
    with zipfile.ZipFile(SOURCE) as z:
        names = z.namelist()
        blobs = {n: z.read(n) for n in names}

    xml = blobs["word/document.xml"].decode("utf-8")
    if PROFILE_PLACEHOLDER in xml:
        raise SystemExit("template already has a PROFILE slot; nothing to do")

    # Insert before the EDUCATION heading paragraph.
    idx = xml.find("EDUCATION")
    if idx < 0:
        raise SystemExit("could not find EDUCATION heading in source docx")
    p_start = max(xml.rfind("<w:p ", 0, idx), xml.rfind("<w:p>", 0, idx))
    if p_start < 0:
        raise SystemExit("could not locate the EDUCATION paragraph start")
    xml = xml[:p_start] + PROFILE_HEADING + PROFILE_BODY + xml[p_start:]
    blobs["word/document.xml"] = xml.encode("utf-8")

    TEMPLATE_DOCX.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TEMPLATE_DOCX, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(n, blobs[n])
    return TEMPLATE_DOCX


if __name__ == "__main__":
    print("built template:", build())
