#!/usr/bin/env python3
import json
import os

SRC = os.path.join(
    "data",
    "Notice_of_competition_scholarship_accommodation_and_degree_award_a.y.2025.26_2026",
    "MinerU_Notice_of_competition_scholarship_accommodation_and_degree_award_a.y.2025.26__20260226084751.json",
)
OUT = os.path.join(
    "data",
    "Notice_of_competition_scholarship_accommodation_and_degree_award_a.y.2025.26_2026",
    "MinerU_simplified.json",
)


def extract_text_from_block(block):
    texts = []
    # Primary: 'lines' -> 'spans' -> 'content'
    for line in (block.get("lines") or []):
        span_texts = []
        for sp in (line.get("spans") or []):
            # prefer plain text, but accept table/html content when present
            c = sp.get("content") or sp.get("html")
            if c:
                span_texts.append(c.strip())
        if span_texts:
            texts.append(" ".join(span_texts))

    # Fallback: nested 'blocks' -> 'lines' -> 'spans'
    if not texts:
        for sub in (block.get("blocks") or []):
            for line in (sub.get("lines") or []):
                for sp in (line.get("spans") or []):
                    c = sp.get("content") or sp.get("html")
                    if c:
                        texts.append(c.strip())

    return " ".join(texts).replace("\n", " ").strip()


def main():
    raw = open(SRC, "r", encoding="utf-8").read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # attempt a tolerant load by removing trailing commas before ] or }
        import re

        cleaned = re.sub(r",\s*([\]}])", r"\1", raw)
        # insert missing commas between numbers separated by whitespace (fix malformed bbox entries)
        cleaned = re.sub(r"(?<=\d)\s+(?=\d)", ", ", cleaned)
        data = json.loads(cleaned)

    out_list = []
    seen_texts = set()
    for page in data.get("pdf_info", []):
        # include both para_blocks and discarded_blocks (headers/footers/page numbers)
        for section in ("para_blocks", "discarded_blocks"):
            for block in (page.get(section) or []):
                if not isinstance(block, dict):
                    continue
                t = block.get("type", "")
                text = extract_text_from_block(block)

                # tables sometimes hold text in nested blocks
                if not text and block.get("type") == "table":
                    parts = []
                    for sub in (block.get("blocks") or []):
                        parts.append(extract_text_from_block(sub))
                    text = " ".join([p for p in parts if p])

                if text and text not in seen_texts:
                    seen_texts.add(text)
                    out_list.append({"type": t, "text": text})

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out_list, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(out_list)} items to {OUT}")


if __name__ == "__main__":
    main()
