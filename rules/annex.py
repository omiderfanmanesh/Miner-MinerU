import re

def annex_rule(item):
    """Detect annex or appendix labels like 'Annex A' or 'Appendix I'
    Returns dict with kind, score, numbering, title, reasons
    """
    text = (item.get("text") or "").strip()
    m = re.match(r"^\s*(?:Annex|Annexo|Appendix|Apêndice)\s+([A-Za-z0-9IVXLCDM]+)\s*[:\.-]?\s*(.*)$", text, re.IGNORECASE)
    if not m:
        return None
    num = m.group(1)
    title = m.group(2).strip()
    return {
        "kind": "annex",
        "score": 95,
        "numbering": num,
        "title": title,
        "raw": text,
        "reasons": ["annex_rule"],
    }
