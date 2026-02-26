import re

def decimal_rule(item):
    """Detect dotted decimal numbering like 2.1 or 10.3.4.2
    Returns dict with keys: kind, score, numbering, title, reasons
    """
    text = (item.get("text") or "").strip()
    m = re.match(r"^\s*(?P<num>\d+(?:\.\d+)+)\s+(?P<title>.+)$", text)
    if not m:
        return None
    numbering = m.group("num")
    title = m.group("title").strip()
    return {
        "kind": "heading",
        "score": 80,
        "numbering": numbering,
        "title": title,
        "raw": text,
        "reasons": ["decimal_rule"],
    }
