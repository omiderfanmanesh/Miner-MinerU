import re

def table_rule(item):
    """Detect items that represent tables. Prefer items with an explicit 'html' key.
    Returns dict with kind, score, html (if present), text (fallback), reasons
    """
    # If the item has html content, treat it as a table block
    if item.get("html"):
        return {
            "kind": "table",
            "score": 100,
            "html": item.get("html"),
            "text": item.get("text"),
            "reasons": ["table_rule_html"],
        }
    text = (item.get("text") or "").strip()
    # simple heuristic: multiple pipes or many columns by repeated spacing
    if text.count("|") >= 2 or re.search(r"\w\s{2,}\w", text):
        return {
            "kind": "table",
            "score": 50,
            "html": None,
            "text": text,
            "reasons": ["table_rule_text"],
        }
    return None
