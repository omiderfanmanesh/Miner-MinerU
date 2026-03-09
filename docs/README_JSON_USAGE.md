# How to Use the JSON File for Better Markdown Extraction

## TL;DR

The JSON file (`data/MinerU_*.json`) contains the **original PDF extraction** with:
- ✅ Better text accuracy (not re-OCR'd markdown)
- ✅ Spatial coordinates (can detect footers, fix ordering)
- ✅ OCR confidence scores (know which parts are unreliable)
- ✅ Block type classification (title/text/list/table already labeled)

**Use it instead of the markdown file as the source of truth for heading correction.**

## What's Inside the JSON

### File Structure
```
data/MinerU_Bando_Borse_di_studio_2025-2026_ENG__20260309145918.json
├─ pdf_info[0]        (Page 1)
│  ├─ para_blocks[0]  (Block 1: title "CALL FOR THE ASSIGNMENT OF")
│  │  ├─ type: "title"
│  │  ├─ lines[0].spans[0]
│  │  │  ├─ content: "CALL FOR THE ASSIGNMENT OF"
│  │  │  ├─ score: 0.993      (OCR confidence)
│  │  │  └─ bbox: [199, 243, 393, 258]
│  │  └─ bbox: [199, 242, 393, 255]  (Spatial coordinates)
│  ├─ para_blocks[1]  (Block 2: title "SCHOLARSHIPS FOR...")
│  └─ para_blocks[...] (more blocks)
├─ pdf_info[1]        (Page 2)
│  └─ para_blocks[...] (blocks on page 2)
└─ ... (23 more pages)
```

### Key Information Available

| Data | How to Extract | Use Case |
|------|---|---|
| **Text** | Aggregate all `span['content']` → join | Better matching (original extraction) |
| **Confidence** | Get `min(span['score'])` | Identify unreliable text |
| **Position** | `bbox[1]` (Y-top), `bbox[3]` (Y-bottom) | Detect footers, fix ordering |
| **Type** | `block['type']` | Filter what to process |
| **Page** | `page_idx` | Cross-reference to PDF |

## Document Statistics

This specific document:
- **24 pages**, **269 blocks total**
- **24 titles** (your heading targets)
- **168 text blocks**, 60 lists, 16 tables, 1 equation
- **Quality**: 23 excellent (>0.95), 1 borderline (0.89), 0 poor (<0.75)

## Step-by-Step Implementation

### Step 1: Parse the JSON

```python
import json
from pathlib import Path

json_path = Path('data/MinerU_Bando_Borse_di_studio_2025-2026_ENG__20260309145918.json')

with open(json_path, encoding='utf-8') as f:
    data = json.load(f)

# Iterate all pages and blocks
for page_idx, page in enumerate(data['pdf_info']):
    print(f"Page {page_idx + 1}")
    for block in page['para_blocks']:
        block_type = block['type']

        # Extract text
        text_parts = []
        for line in block['lines']:
            for span in line['spans']:
                text_parts.append(span['content'])
        text = ' '.join(text_parts)

        print(f"  [{block_type}] {text[:60]}")
```

### Step 2: Extract Useful Information

```python
def extract_blocks(json_path):
    """Parse JSON and return cleaned blocks"""
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)

    blocks = []

    for page_idx, page in enumerate(data['pdf_info']):
        page_height = page['page_size'][1]

        for block in page['para_blocks']:
            # Extract text
            text_parts = []
            scores = []

            for line in block['lines']:
                for span in line['spans']:
                    text_parts.append(span['content'])
                    if 'score' in span:
                        scores.append(span['score'])

            content = ' '.join(text_parts)
            ocr_score = min(scores) if scores else 1.0

            # Check if likely footer
            y_top = block['bbox'][1]
            y_bottom = block['bbox'][3]
            is_likely_footer = (
                (y_top < 50 or y_bottom > page_height - 50) and
                (len(content) < 30 or ocr_score < 0.75)
            )

            blocks.append({
                'type': block['type'],
                'content': content,
                'page': page_idx,
                'y_top': y_top,
                'y_bottom': y_bottom,
                'ocr_score': ocr_score,
                'is_footer': is_likely_footer,
                'bbox': block['bbox'],
            })

    # Sort by page and vertical position
    blocks.sort(key=lambda b: (b['page'], b['y_top']))

    return blocks
```

### Step 3: Use JSON for TOC Matching

```python
def match_toc_entry(toc_entry, json_blocks):
    """Find matching block for TOC entry"""

    # Try exact match first
    for block in json_blocks:
        if (block['type'] == 'title' and
            not block['is_footer'] and
            block['content'].strip() == toc_entry.strip()):
            return (block, 'exact')

    # Try fuzzy match
    import difflib
    best = None
    best_ratio = 0

    for block in json_blocks:
        if block['type'] == 'title' and not block['is_footer']:
            ratio = difflib.SequenceMatcher(
                None,
                toc_entry.lower(),
                block['content'].lower()
            ).ratio()

            if ratio > best_ratio:
                best_ratio = ratio
                best = block

    if best_ratio > 0.80 and best['ocr_score'] > 0.75:
        return (best, 'fuzzy')

    return (None, None)
```

### Step 4: Generate Fixed Markdown

See IMPLEMENTATION_EXAMPLE.md for full code.

## Key Benefits

| Problem | JSON Solution |
|---------|---|
| Text corrupted in markdown | Use original extraction |
| Can't detect footers | Y-position + length + score |
| Wrong block ordering | Sort by spatial coords |
| No quality info | OCR confidence per block |

## Files to Read

1. **JSON_QUICK_REFERENCE.txt** - Quick reference
2. **JSON_STRUCTURE_ANALYSIS.md** - Detailed structure
3. **IMPLEMENTATION_EXAMPLE.md** - Full code examples
4. **JSON_VS_MARKDOWN_COMPARISON.md** - Why JSON is better

## Integration with Pipeline

```bash
# Enhanced version (with JSON)
python -m miner_mineru fix source.md --toc toc.json --json-data data.json --output-dir output/
```

Benefits:
- ✅ Use original JSON text
- ✅ Detect and skip footers
- ✅ Report extraction quality
- ✅ Confidence-aware matching
- ✅ Detailed output report
