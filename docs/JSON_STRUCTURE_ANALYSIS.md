# MinerU JSON Structure Analysis & Usage Guide

## Document Structure Overview

The JSON file contains **raw PDF extraction data** with spatial and textual information for every element on every page.

### Top-Level Structure
```
{
  "pdf_info": [page0, page1, ...],  // Array of 24 pages
  "_backend": "...",
  "_ocr_enable": true,
  "_vlm_ocr_enable": true,
  "_version_name": "..."
}
```

### Per-Page Structure
```
{
  "page_idx": 0,
  "page_size": [width, height],
  "para_blocks": [block0, block1, ...],  // Content blocks
  "discarded_blocks": [...]  // Blocks MinerU considered noise
}
```

### Block Structure (Para_blocks)
```
{
  "type": "title",              // title | text | list | table | interline_equation
  "bbox": [x1, y1, x2, y2],     // Spatial coordinates (y = vertical position)
  "angle": 0,                   // Rotation (usually 0)
  "index": 11,                  // Order on page
  "lines": [
    {
      "bbox": [...],
      "spans": [
        {
          "content": "Art. 1 - Definitions",
          "type": "text",
          "score": 0.961,        // OCR confidence (0-1)
          "bbox": [...]
        }
      ]
    }
  ]
}
```

## Document Statistics

| Metric | Value |
|--------|-------|
| Total Pages | 24 |
| Total Blocks | 269 |
| Titles | 24 (8.9%) |
| Text | 168 (62.5%) |
| Lists | 60 (22.3%) |
| Tables | 16 (5.9%) |
| Equations | 1 (0.4%) |

## What The JSON Contains That's Useful

### 1. **Spatial Information (bbox)**
- **Purpose**: Reconstruct document structure by ordering
- **Format**: `[x1, y1, x2, y2]` where y-coordinate indicates vertical position
- **Use Case**:
  - Identify which elements should be grouped together
  - Detect if titles are actually footers/headers (different y-positions)
  - Reorder blocks if extraction order is wrong
  - Identify titles that appeared as inline text in original PDF

### 2. **Block Type**
- **title**: Headings/structural elements (what we want in TOC)
- **text**: Body paragraphs
- **list**: Enumerated/bulleted lists
- **table**: Tabular data
- **interline_equation**: Mathematical content
- **Use Case**:
  - Filter only titles for TOC
  - Preserve non-title blocks correctly
  - Detect if a title was misclassified as text

### 3. **OCR Confidence Score**
- **Range**: 0.0 - 1.0
- **Use Case**:
  - Flag potentially corrupted text (< 0.85 confidence)
  - Warn user about extraction quality
  - Decide whether fuzzy matching or exact matching applies
  - Identify "footer" text that looks like headings but has low confidence

### 4. **Page & Index Information**
- **page_idx**: Which page (0-23)
- **index**: Order on that page
- **Use Case**:
  - Cross-reference back to original PDF
  - Maintain document ordering
  - Handle split headings across page breaks

## What We DON'T Need

- `bbox` pixel coordinates (x1, x2 are left/right edges)
- `angle` (rotation, almost always 0)
- `discarded_blocks` (noise that MinerU filtered out)
- Full line/span structure (we only need aggregated content)

## How to Use It for Pipeline Improvements

### Problem 1: Mistaken Titles (Text Classified as Title)
**Symptom**: Markdown has many `#` headings that shouldn't be there

**Solution from JSON**:
```python
# Check OCR score - if < 0.80, it might be footer text
if min_span_score < 0.80:
    # Likely footer/footer-like text

# Check vertical position (y-coordinate)
# If y > 400 consistently, might be footer
if block['bbox'][1] > 400 and block['bbox'][3] > 400:
    # Likely footer/repeated element
```

### Problem 2: Missing Titles (Real Headings Not Detected)
**Symptom**: Some article numbers/section names in TOC aren't in markdown

**Solution from JSON**:
```python
# Look at discarded_blocks - might contain missed titles
for block in page['discarded_blocks']:
    if block['type'] == 'title':
        # This was filtered out - check why
        # Maybe nearby text suggests it should be included
```

### Problem 3: Ordering Issues (Headings in Wrong Sequence)
**Symptom**: Extracted markdown has headings in wrong order

**Solution from JSON**:
```python
# Use page_idx + bbox[1] (y-coordinate) for proper ordering
blocks.sort(key=lambda b: (b['page_idx'], b['bbox'][1]))
# Now blocks are in correct reading order
```

### Problem 4: Footers Confused with Headers
**Symptom**: "Page X of Y", document info appearing as headings

**Solution from JSON**:
```python
# Footers typically:
# 1. Very low y-coordinate (top of page) OR high y-coordinate (bottom)
# 2. Repeat on every page
# 3. Very low OCR confidence
# 4. Very short text

def is_likely_footer(block):
    y_top = block['bbox'][1]
    y_bottom = block['bbox'][3]
    text = extract_text(block)
    score = get_min_score(block)

    is_top_footer = y_top < 50
    is_bottom_footer = y_bottom > page_height - 50
    is_short = len(text) < 30
    is_low_confidence = score < 0.75

    return (is_top_footer or is_bottom_footer) and (is_short or is_low_confidence)
```

## Recommended Implementation Approach

### Step 1: Create JSON Parser
Extract useful information from JSON blocks:
```python
def parse_mineru_json(json_path):
    """Convert MinerU JSON to structured document"""
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)

    blocks = []
    for page_idx, page in enumerate(data['pdf_info']):
        page_height = page['page_size'][1]

        for block in page['para_blocks']:
            text = extract_text(block)
            min_score = get_min_score(block)

            blocks.append({
                'type': block['type'],
                'content': text,
                'page': page_idx,
                'y_top': block['bbox'][1],
                'y_bottom': block['bbox'][3],
                'ocr_score': min_score,
                'is_footer': is_likely_footer(block, page_height),
                'bbox': block['bbox'],
                'index': block['index']
            })

    return blocks
```

### Step 2: Filter & Reconstruct
```python
def reconstruct_markdown(json_path, toc_json):
    """Build markdown from JSON with correct structure"""
    blocks = parse_mineru_json(json_path)

    # Filter out footers/noise
    content_blocks = [b for b in blocks if not b['is_footer']]

    # Sort by document order
    content_blocks.sort(key=lambda b: (b['page'], b['y_top']))

    # Build markdown
    markdown = []
    for block in content_blocks:
        if block['type'] == 'title':
            # Match against TOC
            level = find_toc_level(block['content'], toc_json)
            if level:
                markdown.append('#' * level + ' ' + block['content'])
            else:
                # Not in TOC - remove heading marker
                markdown.append(block['content'])
        else:
            # Text/list/table - preserve as-is
            markdown.append(block['content'])

    return '\n\n'.join(markdown)
```

### Step 3: Quality Checks
```python
def validate_extraction(blocks):
    """Check extraction quality"""
    low_confidence = [b for b in blocks if b['ocr_score'] < 0.80]
    if low_confidence:
        print(f"⚠️  {len(low_confidence)} blocks with low OCR confidence")
        for b in low_confidence:
            print(f"   Page {b['page']}: {b['content'][:50]} (score: {b['ocr_score']})")

    footers = [b for b in blocks if b['is_footer']]
    print(f"ℹ️  Detected {len(footers)} potential footers (filtered)")

    return len(low_confidence)
```

## Integration with Current Pipeline

### Current Pipeline
```
markdown → extract_toc() → toc.json → fix_markdown() → fixed.md
```

### Enhanced Pipeline
```
pdf_data.json ─────┐
                   ├→ parse_json() ─→ blocks
                   │
markdown ──────────┤
                   ├→ reconstruct_markdown() ─→ corrected.md
                   │
toc.json ──────────┘
```

### Benefits
1. **Eliminate footer confusion** - JSON tells us exact positions
2. **Recover missed titles** - Check discarded_blocks
3. **Better TOC matching** - Use exact text from source + positioning info
4. **Quality metrics** - Show user OCR confidence, detected issues
5. **Reordering capability** - Fix extraction order using spatial data

## Next Steps to Implement

1. ✅ **Understand JSON structure** (you are here)
2. Create `json_parser.py` with `parse_mineru_json()` function
3. Create `footer_detector.py` with heuristics for footer/header identification
4. Modify `md_fixer.py` to accept optional JSON input
5. Update CLI to accept both markdown + JSON for improved correction
6. Add `--use-json` flag to pipeline runner
7. Add quality report showing OCR issues, detected footers, etc.

## Example Usage

```bash
# Current way (markdown only)
python -m miner_mineru fix input.md --toc toc.json --output-dir output/

# Enhanced way (with JSON for better accuracy)
python -m miner_mineru fix input.md --toc toc.json --json-data data.json --output-dir output/
```

Output report would show:
```
✅ Extraction Quality Report
─────────────────────────────
Pages processed: 24
Blocks extracted: 269
  - Titles: 24
  - Text: 168
  - Lists: 60
  - Tables: 16
  - Equations: 1

⚠️  Quality Issues
  - Low OCR confidence: 3 blocks (< 0.80)
  - Detected footers: 7 (filtered)

✅ TOC Matching
  - Matched: 18 entries
  - Fuzzy matched: 2 entries
  - Unmatched: 0 entries
  - Demoted: 6 non-TOC headings
```
