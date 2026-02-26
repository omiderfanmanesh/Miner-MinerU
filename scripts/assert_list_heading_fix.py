import json
import os
import re

BASE = os.path.join(
    "data",
    "Notice_of_competition_scholarship_accommodation_and_degree_award_a.y.2025.26_2026",
    "structure_outputs",
)

def load_report():
    with open(os.path.join(BASE, "report.json"), "r", encoding="utf-8") as f:
        return json.load(f)

def check_report_for_list_false_headings(report):
    false_headings = []
    for it in report.get("items", []):
        orig_type = (it.get("type") or "").lower()
        cls = it.get("classification") or {}
        kind = cls.get("kind") if isinstance(cls, dict) else None
        if orig_type == "list" and kind == "heading":
            false_headings.append({"index": it.get("index"), "text": it.get("text"), "classification": cls})
    return false_headings

def check_clean_md_lists():
    path = os.path.join(BASE, "clean.md")
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Find heading lines that look like they are enumerations (bad)
    bad_heading_lines = []
    for i,l in enumerate(lines):
        if l.lstrip().startswith("#"):
            # Strip leading hashes and whitespace
            rest = re.sub(r"^\s*#+\s*", "", l)
            if re.match(r"^(\d+\.|[a-zA-Z]\.|[•\-])\s", rest):
                bad_heading_lines.append({"line_no": i+1, "line": l.strip()})

    # Find proper list lines (ordered or bullets)
    list_lines = [l for l in lines if re.match(r"^\s*\d+\.\s+", l) or re.match(r"^\s*[-\*]\s+", l)]

    return bad_heading_lines, list_lines

def main():
    report = load_report()
    false_headings = check_report_for_list_false_headings(report)
    bad_heading_lines, list_lines = check_clean_md_lists()

    result = {
        "false_headings_count": len(false_headings),
        "false_headings_examples": false_headings[:5],
        "bad_heading_lines_count": len(bad_heading_lines),
        "bad_heading_lines_examples": bad_heading_lines[:5],
        "list_lines_count": len(list_lines),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
