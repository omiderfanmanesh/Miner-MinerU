#!/usr/bin/env python3
"""
Deterministic pipeline to extract document structure from simplified MinerU JSON.

Stages (strict separation):
1. Ingest JSON
2. Heading classification (rule plugins + scoring)
3. Semantic extraction (kind, numbering, title, page)
4. Tree construction (numeric hierarchy + longest-prefix parent)
5. Rendering (clean.md + doc_tree.json + pageIndex.json)
6. Diagnostics report (report.json)

No LLMs. Decisions are logged to report.json for auditability.
"""

import json
import os
import re
from collections import OrderedDict
from datetime import datetime
import sys
# Ensure project root is on sys.path so local packages (rules) can be imported when
# executing the script from the scripts/ directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from rules import PLUGINS

BASE_DIR = os.path.join(
    "data",
    "Notice_of_competition_scholarship_accommodation_and_degree_award_a.y.2025.26_2026",
)
IN_FILE = os.path.join(BASE_DIR, "MinerU_simplified.json")
OUT_DIR = os.path.join(BASE_DIR, "structure_outputs")
os.makedirs(OUT_DIR, exist_ok=True)


def load_input(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def classify_item(item):
    """Return classification dict for an item. Deterministic scoring."""
    text = (item.get("text") or "").strip()
    ttype = (item.get("type") or "").lower()
    score = 0
    reasons = []

    # Hard constraint: blocks of type 'list' must never be classified as headings
    if ttype == "list":
        # detect whether ordered or bullets and split into items
        ordered_split = re.split(r"(?=\d+\.\s)", text)
        if len(ordered_split) > 1:
            items = [s.strip() for s in ordered_split if s.strip()]
            return {"kind": "list", "score": 30, "items": items, "raw": text, "reasons": ["type=list", "ordered_split"]}
        # bullet-style split
        bullet_split = re.split(r"(?=[•\-\*]\s)", text)
        if len(bullet_split) > 1:
            items = [s.strip() for s in bullet_split if s.strip()]
            return {"kind": "list", "score": 30, "items": items, "raw": text, "reasons": ["type=list", "bullet_split"]}
        # single list line - keep as list with one item
        return {"kind": "list", "score": 20, "items": [text], "raw": text, "reasons": ["type=list", "single"]}

    # Signals
    if ttype == "title":
        score += 30; reasons.append("type=title")
    if ttype == "header":
        score += 20; reasons.append("type=header")
    if ttype == "footer":
        score -= 10; reasons.append("type=footer")
    if ttype == "table":
        score += 5; reasons.append("type=table")
    if ttype == "page_number":
        score -= 50; reasons.append("type=page_number")

    # Numbering pattern (e.g., 2.1, 10.3.4)
    # Enumeration guard: if the text looks like an explicit list enumeration,
    # do not allow it to be classified as a heading by plugins or heuristics.
    enum_pattern = re.match(r"^\s*(?:\d+\.\s|[a-zA-Z]\.\s|[•\-]\s)", text)

    # First, consult rule plugins (deterministic, ordered)
    for plugin in PLUGINS:
        try:
            cand = plugin(item)
        except Exception:
            # plugin errors should not break the pipeline
            reasons.append(f"plugin_error:{getattr(plugin,'__name__',str(plugin))}")
            cand = None
        if cand:
            # merge base signals score with plugin score
            merged = dict(cand)
            merged_score = score + int(cand.get("score", 0))
            merged["score"] = merged_score
            merged_reasons = reasons + cand.get("reasons", [])
            merged["reasons"] = merged_reasons
            # ensure raw/title fallbacks
            merged.setdefault("raw", text)
            merged.setdefault("title", merged.get("title") or merged.get("raw"))
            # Enforce heading-type constraints: only 'title' or 'header' blocks
            # may be treated as headings. Also, enumeration lines must not be
            # classified as headings.
            allowed_heading_types = {"title", "header"}
            if merged.get("kind") == "heading":
                if ttype not in allowed_heading_types:
                    # suppress heading classification for disallowed block types
                    reasons.append("suppressed_heading_by_type")
                    continue
                if enum_pattern:
                    # suppress heading classification for enumerations
                    reasons.append("suppressed_heading_by_enumeration")
                    continue
            return merged

    m = re.match(r"^\s*(?:Article\s+|Art\.\s*)?(?P<num>\d+(?:\.\d+)*)[\)\.:\-\s]+(?P<title>.+)$",
                 text, flags=re.I)
    if m:
        score += 50
        numbering = m.group("num")
        title = m.group("title").strip()
        reasons.append("explicit_numbering")
        return {
            "kind": "heading",
            "score": score,
            "numbering": numbering,
            "title": title,
            "raw": text,
            "reasons": reasons,
        }

    # Leading dotted numbering: "1.2 Title" or "1) Title"
    m2 = re.match(r"^\s*(?P<num>\d+(?:\.\d+)*)(?:[\)\.:\-\s]+)(?P<title>.+)$", text)
    if m2:
        score += 45
        numbering = m2.group("num")
        title = m2.group("title").strip()
        reasons.append("dotted_numbering")
        return {
            "kind": "heading",
            "score": score,
            "numbering": numbering,
            "title": title,
            "raw": text,
            "reasons": reasons,
        }

    # All-caps short line -> likely heading
    words = text.split()
    if text.isupper() and len(words) <= 8 and len(text) > 2:
        score += 20; reasons.append("all_caps_short")
        return {"kind": "heading", "score": score, "numbering": None, "title": text, "raw": text, "reasons": reasons}

    # Type signals
    if ttype in ("title", "header"):
        score += 10; reasons.append(f"type_signal:{ttype}")
        return {"kind": "heading", "score": score, "numbering": None, "title": text, "raw": text, "reasons": reasons}

    if ttype in ("table",):
        return {"kind": "table", "score": score, "numbering": None, "title": text, "raw": text, "reasons": reasons}

    if ttype in ("image",):
        return {"kind": "image", "score": score, "numbering": None, "title": None, "raw": text, "reasons": reasons}

    if ttype == "page_number":
        # page numbers are used to track pages
        pg = None
        if re.match(r"^\d+$", text):
            pg = int(text)
        return {"kind": "page_number", "score": score, "page": pg, "raw": text, "reasons": reasons}

    # Default: paragraph
    return {"kind": "paragraph", "score": score, "numbering": None, "title": None, "raw": text, "reasons": reasons}


def parse_numbering(numstr):
    return [int(p) for p in numstr.split(".") if p != ""]


def build_tree(items, report):
    """Construct hierarchical tree from classified items.

    items: list of dict with keys: kind, title, numbering, raw, page, score
    report: dict to record decisions
    """
    nodes = []
    prefix_map = {}  # prefix str -> node index
    stack = []  # current heading stack of node indices

    current_page = None
    headings = []

    for idx, it in enumerate(items):
        kind = it["kind"]
        raw = it.get("raw")
        # update page
        if kind == "page_number":
            current_page = it.get("page")
            report["events"].append({"type": "page_detected", "index": idx, "page": current_page, "raw": raw})
            continue

        if kind == "heading":
            numbering = it.get("numbering")
            title = it.get("title") or raw
            if numbering:
                parts = parse_numbering(numbering)
                depth = len(parts)
                prefix = ".".join(str(p) for p in parts)
                # find parent by longest-prefix
                parent_idx = None
                for L in range(len(parts)-1, 0, -1):
                    parent_prefix = ".".join(str(p) for p in parts[:L])
                    if parent_prefix in prefix_map:
                        parent_idx = prefix_map[parent_prefix]
                        break
                node = {
                    "id": f"h{len(nodes)+1}",
                    "numbering": prefix,
                    "title": title,
                    "depth": depth,
                    "kind": "numbered",
                    "page": current_page,
                    "content": [],
                    "children": [],
                }
                nodes.append(node)
                nodes_idx = len(nodes)-1
                prefix_map[prefix] = nodes_idx
                if parent_idx is not None:
                    nodes[parent_idx]["children"].append(nodes_idx)
                else:
                    # top-level
                    pass
                stack = stack[:depth-1] + [nodes_idx]
                headings.append(nodes_idx)
                continue

            # heading without numbering
            # heuristics: if type was title -> depth 1, else attach to nearest parent
            depth = 1 if (it.get("reasons") and any(r.startswith("type_signal:title") or r=="type=title" for r in it.get("reasons",[]))) else (len(stack) or 1)
            node = {
                "id": f"h{len(nodes)+1}",
                "numbering": None,
                "title": title,
                "depth": depth,
                "kind": "unnumbered",
                "page": current_page,
                "content": [],
                "children": [],
            }
            nodes.append(node)
            nodes_idx = len(nodes)-1
            # attach to nearest parent
            parent_idx = stack[-1] if stack else None
            if parent_idx is not None:
                nodes[parent_idx]["children"].append(nodes_idx)
            stack = stack[:depth-1] + [nodes_idx]
            headings.append(nodes_idx)
            report["warnings"].append({"type": "ambiguous_heading_assigned", "index": idx, "title": title, "depth": depth})
            continue

        # paragraph/table/image attach to most recent heading
        target_idx = stack[-1] if stack else None
        if target_idx is None:
            # create implicit root heading if none
            node = {
                "id": f"h{len(nodes)+1}",
                "numbering": None,
                "title": "__ROOT__",
                "depth": 0,
                "kind": "root",
                "page": current_page,
                "content": [],
                "children": [],
            }
            nodes.append(node)
            target_idx = len(nodes)-1
            stack = [target_idx]

        if kind in ("paragraph", "table"):
            nodes[target_idx]["content"].append({"kind": kind, "text": it.get("raw"), "page": current_page})
        else:
            nodes[target_idx]["content"].append({"kind": kind, "text": it.get("raw"), "page": current_page})

    # Build hierarchical JSON structure (replace child idx with objects)
    def build_node_obj(i):
        n = nodes[i]
        return {
            "id": n["id"],
            "numbering": n.get("numbering"),
            "title": n.get("title"),
            "depth": n.get("depth"),
            "kind": n.get("kind"),
            "page": n.get("page"),
            "content": n.get("content"),
            "children": [build_node_obj(ci) for ci in n.get("children",[])],
        }

    roots = [build_node_obj(i) for i in range(len(nodes)) if nodes[i]["depth"] in (0,1) and not any(i in nodes[j]["children"] for j in range(len(nodes)))]

    # page index: map pages to headings (id, title)
    page_map = OrderedDict()
    for i,n in enumerate(nodes):
        if n.get("page") is not None:
            page_map.setdefault(str(n.get("page")), []).append({"id": n["id"], "title": n["title"]})

    return {"roots": roots, "nodes": nodes}, page_map


def render_markdown(tree, report=None):
    lines = []
    # traverse roots in order
    def render_node(n):
        depth = max(1, n.get("depth",1))
        depth = min(depth, 6)
        heading = (n.get("numbering") + " ") if n.get("numbering") else ""
        title = n.get("title", "") or ""

        # If the title itself begins with a bullet or enumeration marker,
        # render it as a list instead of a heading and record the conversion.
        if re.match(r"^\s*(?:[•\-\*]\s|\d+\.\s|[a-zA-Z]\.\s)", title):
            if report is not None:
                report.setdefault("events", []).append({"type": "converted_heading_to_list", "id": n.get("id"), "title": title})
            # render the title as list items
            # handle ordered enumerations inside the title
            if re.search(r"^\s*\d+\.\s", title):
                parts = [p.strip() for p in re.split(r"(?=\d+\.\s)", title) if p.strip()]
                for p in parts:
                    item_text = re.sub(r"^\s*\d+\.\s*", "", p).strip()
                    lines.append(f"1. {item_text}")
            elif re.search(r"^\s*[•\-\*]\s", title):
                parts = [p.strip() for p in re.split(r"(?=[•\-\*]\s)", title) if p.strip()]
                for p in parts:
                    item_text = re.sub(r"^\s*[•\-\*]\s*", "", p).strip()
                    lines.append(f"- {item_text}")
            else:
                # letter enumeration or unknown - render as bullet
                parts = [p.strip() for p in re.split(r"(?=[a-zA-Z]\.\s)", title) if p.strip()]
                for p in parts:
                    item_text = re.sub(r"^\s*[a-zA-Z]\.\s*", "", p).strip()
                    lines.append(f"- {item_text}")
        else:
            lines.append("#" * depth + " " + heading + title)
        for c in n.get("content", []):
            kind = c.get("kind")
            text = c.get("text") or c.get("raw") or ""
            if kind == "table":
                lines.append("\n[table]\n")
                lines.append(text)
            elif kind == "list":
                # If the list item contains multiple numbered items in one
                # string, split into separate items. Otherwise render bullets
                # or ordered lists based on item text.
                # detect ordered items like '1. ...'
                if re.search(r"^\s*\d+\.\s", text):
                    parts = [p.strip() for p in re.split(r"(?=\d+\.\s)", text) if p.strip()]
                    for p in parts:
                        # ensure item text without leading enumeration
                        item_text = re.sub(r"^\s*\d+\.\s*", "", p).strip()
                        lines.append(f"1. {item_text}")
                elif re.search(r"^\s*[•\-\*]\s", text):
                    parts = [p.strip() for p in re.split(r"(?=[•\-\*]\s)", text) if p.strip()]
                    for p in parts:
                        item_text = re.sub(r"^\s*[•\-\*]\s*", "", p).strip()
                        lines.append(f"- {item_text}")
                else:
                    # single-line list content
                    lines.append(f"- {text.strip()}")
            else:
                lines.append("")
                lines.append(text)
        for child in n.get("children", []):
            render_node(child)

    for r in tree.get("roots", []):
        render_node(r)

    return "\n\n".join(lines)


def main():
    items = load_input(IN_FILE)

    report = {"generated_at": datetime.utcnow().isoformat() + "Z", "items": [], "warnings": [], "events": []}

    classified = []
    for i, it in enumerate(items):
        cls = classify_item(it)
        # preserve original order and attach index
        entry = {"index": i, "type": it.get("type"), "text": it.get("text"), "classification": cls}
        report["items"].append(entry)
        # normalize classification dict for pipeline
        norm = {
            "kind": cls.get("kind"),
            "numbering": cls.get("numbering"),
            "title": cls.get("title"),
            "raw": cls.get("raw"),
            "page": cls.get("page") if cls.get("kind") == "page_number" else None,
            "reasons": cls.get("reasons"),
        }
        classified.append(norm)

    tree_obj, page_map = build_tree(classified, report)

    # write doc_tree.json
    doc_tree_path = os.path.join(OUT_DIR, "doc_tree.json")
    with open(doc_tree_path, "w", encoding="utf-8") as f:
        json.dump(tree_obj, f, ensure_ascii=False, indent=2)

    # write pageIndex.json
    page_index_path = os.path.join(OUT_DIR, "pageIndex.json")
    with open(page_index_path, "w", encoding="utf-8") as f:
        json.dump({"page_map": page_map}, f, ensure_ascii=False, indent=2)

    # write clean.md
    md = render_markdown(tree_obj)
    md_path = os.path.join(OUT_DIR, "clean.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    # write report
    report_path = os.path.join(OUT_DIR, "report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("Wrote:")
    print(" -", doc_tree_path)
    print(" -", page_index_path)
    print(" -", md_path)
    print(" -", report_path)


if __name__ == "__main__":
    main()
