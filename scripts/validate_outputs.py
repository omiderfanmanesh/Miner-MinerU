import json
import os

BASE = os.path.join(
    "data",
    "Notice_of_competition_scholarship_accommodation_and_degree_award_a.y.2025.26_2026",
    "structure_outputs",
)

def load_json(name):
    p = os.path.join(BASE, name)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    report = load_json("report.json")
    doc = load_json("doc_tree.json")
    page = load_json("pageIndex.json")
    md_path = os.path.join(BASE, "clean.md")
    md = open(md_path, "r", encoding="utf-8").read()

    summary = {
        "report_items": len(report.get("items", [])),
        "report_warnings": len(report.get("warnings", [])),
        "report_events": len(report.get("events", [])),
        "doc_nodes": len(doc.get("nodes", [])),
        "doc_roots": len(doc.get("roots", [])),
        "pageIndex_pages": len(page.get("page_map", {})),
        "clean_md_bytes": len(md.encode("utf-8")),
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
