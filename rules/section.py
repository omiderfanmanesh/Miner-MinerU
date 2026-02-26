import re

def section_rule(item):
    """Detect sections labeled with roman numerals or 'Section I' patterns.
    Returns dict with kind, score, numbering, title, reasons
    """
    text = (item.get("text") or "").strip()
    # Section 1, Section I, SEÇÃO I
    m = re.match(r"^\s*(?:Section|Sec\.|SEÇÃO|Seção)\s+([IVXLCDM0-9]+)\s*[:\.-]?\s*(.*)$", text, re.IGNORECASE)
    if m:
        num = m.group(1)
        title = m.group(2).strip()
        return {
            "kind": "section",
            "score": 85,
            "numbering": num,
            "title": title,
            "raw": text,
            "reasons": ["section_rule"],
        }
    return None
