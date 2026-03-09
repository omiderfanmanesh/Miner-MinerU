# Implementation Example: Using JSON for Better Markdown Generation

## The Problem You Face Now

When MinerU extracts a PDF → Markdown, you get:
1. **OCR artifacts** - Some text is garbled or misrecognized
2. **Wrong classification** - Footers marked as titles, titles marked as text
3. **Wrong ordering** - Blocks in wrong sequence
4. **No confidence info** - Can't tell which parts are unreliable

Then you try to fix with existing markdown + TOC, and it's hard because:
- You're matching against corrupted text
- You can't tell what's real vs what's OCR noise
- You can't order things properly

## The Solution: Use the JSON Instead

The JSON file has the **original extraction from PDF** with:
1. ✅ **Better text accuracy** (extracted directly from PDF, not re-OCR'd)
2. ✅ **Spatial information** (pixel coordinates for ordering)
3. ✅ **Confidence scores** (know which parts are reliable)
4. ✅ **Block type classification** (already knows what's title vs text)

## Implementation in 3 Steps

### Step 1: Parse JSON into Clean Blocks

```python
# miner_mineru/pipeline/json_parser.py

import json
from typing import List, TypedDict
from pathlib import Path

class Block(TypedDict):
    """Simplified block structure from MinerU JSON"""
    type: str              # title, text, list, table, interline_equation
    content: str           # Extracted text
    page: int              # Page number (0-indexed)
    y_top: float           # Top Y coordinate (for ordering)
    y_bottom: float        # Bottom Y coordinate
    ocr_score: float       # Min OCR confidence in block (0-1)
    is_likely_footer: bool # Heuristic: is this a footer?
    index: int             # Order on page


def parse_mineru_json(json_path: Path) -> List[Block]:
    """
    Parse MinerU JSON into simplified blocks.

    Returns blocks sorted by (page, y_position) for correct reading order.
    """
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)

    blocks = []

    for page_idx, page in enumerate(data['pdf_info']):
        page_height = page['page_size'][1]

        for block in page['para_blocks']:
            # Extract aggregated text
            text_parts = []
            scores = []

            for line in block.get('lines', []):
                for span in line.get('spans', []):
                    text_parts.append(span.get('content', ''))
                    if 'score' in span:
                        scores.append(span['score'])

            content = ' '.join(text_parts)
            min_score = min(scores) if scores else 1.0

            # Detect footers (top/bottom of page + short text + low confidence)
            y_top = block['bbox'][1]
            y_bottom = block['bbox'][3]
            is_footer = (
                (y_top < 50 or y_bottom > page_height - 50) and
                (len(content) < 30 or min_score < 0.75)
            )

            blocks.append({
                'type': block.get('type'),
                'content': content,
                'page': page_idx,
                'y_top': y_top,
                'y_bottom': y_bottom,
                'ocr_score': min_score,
                'is_likely_footer': is_footer,
                'index': block.get('index'),
            })

    # Sort by document order: page, then Y-position
    blocks.sort(key=lambda b: (b['page'], b['y_top']))

    return blocks
```

### Step 2: Filter and Match Against TOC

```python
# miner_mineru/pipeline/md_fixer.py (modified)

from json_parser import parse_mineru_json, Block
import difflib

def match_toc_entry_to_json_block(toc_entry, json_blocks):
    """
    Find the best matching block for a TOC entry.

    Returns (block, method) where method is 'exact', 'fuzzy', or None
    """
    # Extract numbering from TOC entry
    numbering = extract_numbering(toc_entry)  # e.g., "Art. 1" from "Art. 1 - Definitions"

    # Step 1: Try exact title match
    for block in json_blocks:
        if block['type'] == 'title' and not block['is_likely_footer']:
            if block['content'].strip() == toc_entry.strip():
                return (block, 'exact')

    # Step 2: Try numbering match (more reliable)
    if numbering:
        for block in json_blocks:
            if block['type'] == 'title' and not block['is_likely_footer']:
                if numbering in block['content']:
                    # Check confidence
                    if block['ocr_score'] > 0.75:
                        return (block, 'exact')

    # Step 3: Try fuzzy match on title
    best_match = None
    best_ratio = 0

    for block in json_blocks:
        if block['type'] == 'title' and not block['is_likely_footer']:
            ratio = difflib.SequenceMatcher(None,
                                           toc_entry.lower(),
                                           block['content'].lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = block

    if best_ratio > 0.80:  # Fuzzy threshold
        return (best_match, 'fuzzy')

    return (None, None)


def reconstruct_markdown_from_json(json_path, toc_json_path, output_path):
    """
    Build corrected markdown directly from JSON source.

    This avoids OCR artifacts by working from original PDF extraction.
    """
    # Parse JSON blocks
    json_blocks = parse_mineru_json(json_path)

    # Load TOC
    with open(toc_json_path) as f:
        toc_data = json.load(f)
    toc_entries = toc_data['entries']  # Assuming this structure

    # Create mapping: TOC entry → block
    matched_blocks = set()
    toc_mapping = {}

    for entry in toc_entries:
        block, method = match_toc_entry_to_json_block(entry, json_blocks)
        if block:
            matched_blocks.add(id(block))
            toc_mapping[entry] = (block, method)

    # Build markdown
    markdown_lines = []
    corrections = {
        'matched': 0,
        'fuzzy': 0,
        'demoted': 0,
        'unmatched_toc': [],
    }

    for block in json_blocks:
        # Skip footers
        if block['is_likely_footer']:
            continue

        # Skip very low confidence
        if block['ocr_score'] < 0.60:
            continue

        # Check if this block is a matched TOC entry
        is_matched = id(block) in matched_blocks

        if block['type'] == 'title':
            if is_matched:
                # Find the TOC entry and get correct level
                entry, (matched_block, method) = [
                    (e, m) for e, m in toc_mapping.items()
                    if id(m[0]) == id(block)
                ][0]

                kind = entry.get('kind')  # section, article, subarticle, etc.
                level = {
                    'section': 1,
                    'article': 2,
                    'subarticle': 3,
                    'subsection': 3,
                    'topic': 4,
                }.get(kind, 2)

                markdown_lines.append('#' * level + ' ' + block['content'])
                corrections['matched' if method == 'exact' else 'fuzzy'] += 1
            else:
                # Not in TOC - demote to plain text
                markdown_lines.append(block['content'])
                corrections['demoted'] += 1
        else:
            # Text, list, table - preserve as-is
            markdown_lines.append(block['content'])

    # Check for unmatched TOC entries
    for entry in toc_entries:
        if entry not in toc_mapping:
            corrections['unmatched_toc'].append(entry.get('content'))

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(markdown_lines))

    return corrections
```

### Step 3: Generate Quality Report

```python
def generate_quality_report(json_path, corrections):
    """Generate report showing extraction quality and corrections made"""

    json_blocks = parse_mineru_json(json_path)

    # Analyze blocks
    total_blocks = len(json_blocks)
    titles = [b for b in json_blocks if b['type'] == 'title']
    footers = [b for b in json_blocks if b['is_likely_footer']]
    low_confidence = [b for b in json_blocks if b['ocr_score'] < 0.80]

    report = {
        'extraction_quality': {
            'total_blocks': total_blocks,
            'titles_found': len(titles),
            'detected_footers': len(footers),
            'low_confidence_blocks': len(low_confidence),
            'avg_ocr_score': sum(b['ocr_score'] for b in json_blocks) / len(json_blocks),
        },
        'toc_matching': {
            'matched_exact': corrections['matched'],
            'matched_fuzzy': corrections['fuzzy'],
            'demoted_non_toc': corrections['demoted'],
            'unmatched_toc_entries': corrections['unmatched_toc'],
        },
        'quality_issues': []
    }

    # Flag issues
    if low_confidence:
        for b in low_confidence:
            report['quality_issues'].append({
                'type': 'low_ocr_confidence',
                'page': b['page'] + 1,
                'content': b['content'][:50],
                'score': b['ocr_score'],
            })

    if corrections['unmatched_toc']:
        for entry in corrections['unmatched_toc']:
            report['quality_issues'].append({
                'type': 'missing_from_source',
                'toc_entry': entry,
                'recommendation': 'Add to source document or remove from TOC',
            })

    return report
```

## CLI Usage

```bash
# Old way (markdown → markdown, with TOC guidance)
python -m miner_mineru fix source.md --toc toc.json

# New way (JSON → markdown, using original PDF extraction)
python -m miner_mineru fix source.md --toc toc.json --json-data pdf_data.json

# Get quality report
python -m miner_mineru fix source.md --toc toc.json --json-data pdf_data.json --report
```

## Key Differences

| Aspect | Old Way (Markdown) | New Way (JSON) |
|--------|-------------------|------------------|
| **Source** | OCR'd markdown (already corrupted) | Original PDF extraction |
| **Titles** | What markdown contains | What JSON classified as title |
| **Ordering** | Order in markdown file | Spatial order (page + y-coordinate) |
| **Footers** | Can't detect/remove | Can detect by Y-position + length + score |
| **Confidence** | No info | OCR score per block |
| **Matching** | Against corrupted text | Against original extraction |
| **Quality** | Unknown | Reports OCR issues found |

## Benefits

1. **Better accuracy** - Working from original PDF extraction, not markdown OCR artifacts
2. **Natural ordering** - Spatial coordinates guarantee correct sequence
3. **Footer removal** - Can detect and skip document headers/footers
4. **Quality insights** - See which parts are unreliable
5. **Fewer API calls** - No need for LLM to infer bad matches (JSON tells us the facts)

## Example: The Bando Borse Document

Before (using markdown):
- Title "A-Revocationforfeiture of te scholarshipand relati" (OCR error)
- Multiple unmatched headings (can't tell if real or OCR noise)
- No way to remove footers (don't know where they are)

After (using JSON):
- See exact extraction "A - Revocation/forfeiture of the scholarship..." (OCR score: 0.89)
- Know which blocks are footers (Y < 50 or Y > 791)
- Match with confidence awareness
- Report shows "1 title with low OCR score"

The JSON is the **bridge between noisy markdown and correct structure**.
