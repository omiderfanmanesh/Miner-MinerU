import re

def article_rule(item):
    """Detect article headings like 'Article 1.' or 'Art. 1' or 'ARTIGO 1' (multi-language)
    Returns dict with keys: kind, score, numbering, title, reasons
    """
    text = (item.get("text") or "").strip()
    # common forms: Article 1. Title..., Art. 2 - Title
    m = re.match(r"^\s*(?:Article|Art\.|Artigo|ARTIGO|ART)\s*\.?\s*(?P<num>\d+)\s*[:\.\-]?\s*(?P<title>.*)$", text, re.IGNORECASE)
    if not m:
        return None
    num = m.group("num")
    title = m.group("title").strip()
    return {
        "kind": "article",
        "score": 90,
        "numbering": num,
        "title": title,
        "raw": text,
        "reasons": ["article_rule"],
    }
