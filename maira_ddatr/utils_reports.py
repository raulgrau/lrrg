"""
utils_reports.py
Lightweight section parser for MIMIC-CXR free-text reports.

MIMIC reports are semi-structured: a "FINAL REPORT" banner followed by
labelled sections (EXAMINATION, INDICATION, TECHNIQUE, COMPARISON, FINDINGS,
IMPRESSION, ...). We detect a fixed set of *known* section headers (rather than
any "Word:" token) so we don't mis-split on phrases like "the following:".
"""

import re

# Known section headers (lowercased). Longest matched first so multi-word
# headers win over their single-word prefixes.
KNOWN = [
    "final report", "examination", "indication", "clinical history",
    "clinical information", "history", "comparison", "comparisons",
    "technique", "findings", "impression", "impressions",
    "reason for exam", "reason for examination", "wet read",
    "recommendation", "recommendations", "conclusion", "notification",
]
_KNOWN_SORTED = sorted(KNOWN, key=len, reverse=True)
_HEADER_RE = re.compile(
    r"(?i)(?:(?<=\n)|(?<=^)|(?<=\s))("
    + "|".join(re.escape(k) for k in _KNOWN_SORTED)
    + r")\s*:"
)


def parse_sections(text: str) -> dict:
    """Return {section_name_lower: content}. First occurrence wins; dups appended."""
    if not text:
        return {}
    text = text.replace("\r", "\n")
    matches = list(_HEADER_RE.finditer(text))
    out = {}
    for i, m in enumerate(matches):
        name = m.group(1).strip().lower()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = re.sub(r"\s+", " ", text[start:end]).strip()
        if not content:
            continue
        out[name] = (out[name] + " " + content) if name in out else content
    return out


def get_findings(text: str) -> str:
    """Findings section (the generation target). '' if absent."""
    s = parse_sections(text)
    return s.get("findings", "").strip()


def get_prior_report(text: str) -> str:
    """
    Text to feed MAIRA-2 as `prior_report`. Prefer the prior FINDINGS; fall back
    to IMPRESSION; finally to the whole narrative with the FINAL REPORT banner
    and section labels stripped.
    """
    s = parse_sections(text)
    if s.get("findings"):
        return s["findings"].strip()
    if s.get("impression"):
        return s["impression"].strip()
    if s.get("impressions"):
        return s["impressions"].strip()
    # last resort: strip banner + collapse
    cleaned = re.sub(r"(?i)\bfinal report\b", " ", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def get_field(text: str, field: str) -> str:
    """Pull a single section by canonical name with light fallbacks."""
    s = parse_sections(text)
    field = field.lower()
    if field == "indication":
        for k in ("indication", "reason for exam", "reason for examination",
                  "history", "clinical history", "clinical information"):
            if s.get(k):
                return s[k].strip()
        return ""
    if field == "comparison":
        for k in ("comparison", "comparisons"):
            if s.get(k):
                return s[k].strip()
        return ""
    return s.get(field, "").strip()
