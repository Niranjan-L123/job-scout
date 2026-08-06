"""Resume-tailoring pipeline: turn liked job URLs into tailored CVs.

Deterministic plumbing lives here (fetch JD, sync master, write docx, log
tracker); the actual tailoring judgement is done by Claude via the
resume-tailor skill. Reuses the job-scout scraper's HTTP session / truststore.
"""
from pathlib import Path

# The user's resume workspace (data only: docx, master.md, tracker).
RESUME_ROOT = Path(r"C:\Workspace\Personal\resume")
MASTER_DOCX = RESUME_ROOT / "master" / "Niranjan_Lakshminarasimhan_CV_Master.docx"
MASTER_MD = RESUME_ROOT / "master" / "master.md"
# Polished single-page template for output. Built from the Verkada layout with
# a tailored PROFILE slot at the top (see tailor/build_template.py).
TEMPLATE_DOCX = RESUME_ROOT / "master" / "Niranjan_Lakshminarasimhan_CV_Template.docx"
# Exact placeholder text sitting in the template's profile line; the tailoring
# step replaces it with a job-specific, ATS-keyword-rich profile.
PROFILE_PLACEHOLDER = "PROFILE_PLACEHOLDER"
TRACKER = RESUME_ROOT / "Job_Applications_Tracker.xlsx"
SHORTLIST = Path(__file__).resolve().parent.parent / "data" / "shortlist.txt"
