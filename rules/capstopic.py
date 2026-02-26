import re

def capstopic_rule(item):
    """Detect short all-caps topic lines like 'ADMISSIONS' or 'APPLICATIONS AND FEES'
    Returns dict with kind, score, title, reasons
    """
    text = (item.get("text") or "").strip()
    # reject long lines; prefer short headings under ~60 chars
    if len(text) == 0 or len(text) > 80:
        return None
    # allow letters, numbers, ampersand, spaces
    if re.fullmatch(r"[A-Z0-9 &\-()\.,']+", text) and any(c.isalpha() for c in text):
        return {
            "kind": "topic",
            "score": 60,
            "title": text.title(),
            "raw": text,
            "reasons": ["capstopic_rule"],
        }
    return None
