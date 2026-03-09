# JSON vs Markdown: Side-by-Side Comparison

## Problem: Why Current Markdown Approach Is Limited

When MinerU extracts PDF → Markdown, the markdown file is already once-corrupted:
1. PDF → (MinerU OCR) → Markdown (errors introduced)
2. Markdown → (Your TOC matching) → Fixed Markdown (harder to match because source is corrupted)

When you try to fix using markdown + TOC:
- You're matching against corrupted text
- You don't know if a heading is real or OCR noise
- You can't detect/remove footers
- You can't reorder if blocks are in wrong sequence

## Solution: Use JSON as Source of Truth

The JSON file is the **original extraction from MinerU**, before it was converted to markdown.

### Comparison Table

| Aspect | Markdown File | JSON File |
|--------|---------------|-----------|
| **When Created** | After → PDF | Direct from PDF |
| **Number of OCR Passes** | 1 (PDF → Markdown) | 1 (PDF → JSON) |
| **Text Accuracy** | Lower (some corruption) | Better (no re-OCR) |
| **Spatial Info** | None (lost during conversion) | Exact (bbox coordinates) |
| **Block Type** | Must infer from heading `#` | Explicitly classified |
| **OCR Confidence** | Not provided | Score (0-1) per span |
| **Footers/Headers** | Can't detect | Can detect (Y < 50 or Y > 791) |
| **Ordering** | Trust markdown order | Can sort by spatial position |
| **Can Recover Lost Blocks** | No | Yes (check discarded_blocks) |

## Example: Page 17 Low-Confidence Title

### What You See in Markdown
```markdown
# A-Revocationforfeiture of te scholarshipand relati
```

**Problem**: This looks like a real heading (has `#`), but:
- Is it OCR-corrupted?
- Is it really a heading or just a side note?
- Should it be in TOC or removed?
- Unknown!

### What JSON Shows
```json
{
  "type": "title",
  "bbox": [220, 293, 420, 305],
  "content": "A-Revocationforfeiture of te scholarshipand relati",
  "ocr_score": 0.89,
  "page_idx": 16
}
```

**Benefits**:
- ✅ Score 0.89 tells you: "This is borderline quality, check it"
- ✅ Spatial coordinates show exact position
- ✅ Type confirms it's classified as title
- ✅ You can decide: fuzzy-match or require better match

## Example: Detecting Footers

### Markdown Approach
You see a heading and don't know:
```markdown
# Art. 1 - Definitions
```

Is this:
- The real article title? (Yes, should match TOC)
- A page footer? (No, should be removed)
- Unclear from markdown alone!

### JSON Approach
```json
{
  "type": "title",
  "bbox": [214, 35, 378, 48],    // <-- Y=35 is VERY high on page
  "content": "Art. 1 - Definitions",
  "ocr_score": 0.961,
  "page_idx": 1
}
```

**Detection Logic**:
```python
if y_top < 50 and len(content) < 60:
    print("This is likely a HEADER or PAGE NUMBER")
    # Skip it, don't treat as heading
```

Result: Correctly identifies and skips page headers/footers.

## Example: Ordering Issues

### Scenario: Blocks Extracted Out of Order

Markdown might have:
```markdown
# Section A
Some text here
# Art. 2 - Something
More text
# Art. 1 - Something else
```

**Problem**: Is this the correct order? Are articles really numbered wrong?

### JSON Solution
```json
// Block 1
{"type": "title", "content": "Section A", "bbox": [100, 200, ...], "page": 0}

// Block 2
{"type": "title", "content": "Art. 2 - Something", "bbox": [100, 300, ...], "page": 1}

// Block 3
{"type": "title", "content": "Art. 1 - Something else", "bbox": [100, 250, ...], "page": 1}
```

**Fix**: Sort by `(page_idx, bbox[1])`:
1. Page 0, Y=200: "Section A"
2. Page 1, Y=250: "Art. 1 - Something else"
3. Page 1, Y=300: "Art. 2 - Something"

Now the order is correct because you're using spatial coordinates, not markdown order.

## Example: Confidence-Aware Matching

### Scenario: Title with Low Confidence

TOC says: `Art. 11 - Student Welfare Services`

Markdown has: `Art. 11 - Student Welfare Services` (what if OCR corrupted it?)

JSON shows:
```json
{
  "type": "title",
  "content": "Art. 11 - Student Welfare Services",
  "ocr_score": 0.76  // <-- LOW SCORE, be careful
}
```

**Decision Logic**:
```python
if ocr_score > 0.90:
    # Exact match is reliable, use it
    match = "exact"
elif ocr_score > 0.75:
    # Borderline - accept only if TOC numbering matches exactly
    if "Art. 11" in json_text and "Art. 11" in toc_entry:
        match = "fuzzy_with_confidence_check"
    else:
        match = None
else:
    # Too unreliable, skip
    match = None
```

You can **adjust matching strictness** based on confidence!

## Practical Workflow

### Current Workflow (Markdown Only)
```
markdown file
    ↓
[regex extract titles]
    ↓
titles list
    ↓
[fuzzy match against TOC]
    ↓
[guess confidence based on match quality]
    ↓
fixed markdown
```

Problems:
- Working with corrupted text
- Guessing confidence
- No position info
- Can't detect footers

### Improved Workflow (With JSON)
```
markdown file + json file + toc file
    ↓
[parse json blocks]
    ↓
[filter: skip footers, low confidence < 0.60]
    ↓
[sort by (page, y_position)]
    ↓
[match JSON blocks to TOC using numbering + title + confidence]
    ↓
[classify: matched (exact/fuzzy) or demoted]
    ↓
[build markdown from blocks with correct levels]
    ↓
[generate report: matched, unmatched, issues found]
    ↓
fixed markdown + quality report
```

Benefits:
- ✅ Working with original extraction
- ✅ Know actual confidence
- ✅ Correct spatial order
- ✅ Can detect/remove footers
- ✅ Quality metrics

## Document-Specific Insights

### This Document (Bando Borse di studio, 24 pages)

**From JSON Analysis**:
```
Total blocks: 269
  - Titles: 24 (8.9%)
  - Text: 168 (62.5%)
  - Lists: 60 (22.3%)
  - Tables: 16 (5.9%)
  - Equations: 1 (0.4%)

Quality:
  - Excellent titles (score > 0.95): 23
  - Borderline titles (score 0.75-0.95): 1
  - Low confidence (score < 0.75): 0

Potential issues:
  - 1 title with score 0.89 (Page 17: "A-Revocationforfeiture...")
  - 1 suspicious Y-position (Page 2: "Art. 1" at Y=35, might be header)
```

**What This Means**:
- Very high quality extraction overall
- Only 1 questionable title (worth investigating)
- No truly corrupt blocks (all > 0.75)
- Can trust most matches without extra validation

## Implementation Decision

### Option 1: Keep Current Approach
```
Pro: Already works
Con: Limited to markdown quality, no confidence info
```

### Option 2: Enhance with JSON (Recommended)
```
Pro: Better accuracy, confidence info, footer detection, ordering fix
Con: Need to implement parsing + enhanced matching

Cost: ~200 lines of Python code
Benefit: Higher quality output, better reporting, fewer false positives
```

The JSON is **already available** — it costs nothing to use it, and significantly improves output quality.

## Next Steps

1. **Implement json_parser.py**: Parse JSON into simplified blocks (50 lines)
2. **Add footer detection**: Check Y-position + length + score (30 lines)
3. **Enhance matching**: Use JSON text instead of markdown (40 lines)
4. **Add quality report**: Show what was found and any issues (50 lines)
5. **Update CLI**: Add `--json-data` parameter (20 lines)

Total: ~200 lines of Python to unlock all these benefits.

## Example Output Comparison

### Current (Markdown Only)
```
TOC Matching Results
-------------------
Matched: 18 headings
Unmatched: 6 headings
Demoted: 6 non-TOC headings

(No info on quality, confidence, footers)
```

### Enhanced (With JSON)
```
Extraction Quality Report
--------------------------
Pages: 24
Blocks extracted: 269
Titles found: 24

Confidence Analysis:
  Excellent (> 0.95): 23
  Borderline (0.75-0.95): 1 (Page 17, score 0.89)
  Low (< 0.75): 0

Detected Issues:
  Potential header: Page 2, "Art. 1" at Y=35
  Low-confidence: Page 17, "A-Revocationforfeiture..." (score 0.89)

TOC Matching Results
---------------------
Matched exact: 18 entries
Matched fuzzy: 2 entries (with confidence check: > 0.80)
Demoted non-TOC: 6 headings
Unmatched in TOC: 1 entry (truly missing from source)

Recommendations:
  - Title on Page 17 has low confidence (0.89) - verify manually
  - Found 1 missing TOC entry - check if should be added
  - Quality is high overall, safe to use

✅ Markdown generation complete with high confidence
```

Much more useful!
