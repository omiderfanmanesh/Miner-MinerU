# Numbering Priority Matching - March 9, 2026 (Enhancement)

## Problem

Some headings in the source markdown have different titles than what's listed in the TOC, even though they have the same numbering.

**Example**:
- TOC entry: `1.2.4: Career check for candidates enrolled in an additional semester...`
- Source heading: `# 1.2.4 Students enrolled in the open semester or filter semester...`

The old matching logic would **only** match if the title text was similar enough (fuzzy matching >= 0.8 similarity). This meant headings with correct numbering but different titles wouldn't match.

## Solution

Prioritize **numbering** over title matching, because:
1. Numbering is typically unique and reliable across the document
2. Document editors often reword titles but preserve numbering
3. The TOC numbering IS the "ground truth" for hierarchy

## Implementation

Changed the matching logic in `match_toc_to_source()` to use a two-tier approach:

```python
# PRIORITY 1: If entry has numbering, match by numbering FIRST
if num_lower:
    # Find exact numbering match with word boundary
    # This works even if title text differs

# PRIORITY 2: If no numbering, match by title
else:
    # Use exact + substring + fuzzy matching for title-only entries
```

## Result

| Aspect | Before | After | Change |
|--------|--------|-------|--------|
| Matched TOC entries | 85 | 86 | +1 |
| Exact numbering matches | 70 | 79 | +9 |
| Fuzzy title matches | 15 | 7 | -8 |
| Unmatched headings demoted to H4 | 48 | 47 | -1 |
| Unmatched TOC entries | 4 | 3 | -1 |

## Real Document Impact

For Bando di Concorso document:
- Line 291: `# 1.2.4 Students enrolled in the open semester...`
  - **Before**: Demoted to `####` (unmatched)
  - **After**: Correctly matched to TOC `1.2.4` and leveled to `###`

## Test Coverage

✅ All 16 existing tests pass (backward compatible)

## Notes

- This change makes the matching more **robust** for real-world documents where titles may vary
- Numbering is treated as the primary key for matching
- Title matching still works as fallback for entries without numbering
- Fuzzy matching remains as final fallback
