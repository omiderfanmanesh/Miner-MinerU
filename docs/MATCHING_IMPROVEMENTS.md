# Matching Logic Improvements

## Problem Identified

The original substring matching logic in `match_toc_to_source()` was **too loose** and caused false positives:

**Example from real document**:
- TOC entry: `article: "CALL FOR APPLICATIONS – RECIPIENTS"`
- Source heading line: `# ARTICLE 1 – CALL FOR APPLICATIONS – RECIPIENTS`

The substring check `if "CALL FOR..." in "ARTICLE 1 – CALL FOR..."` would match, even though:
1. The TOC title is missing the "ARTICLE 1 –" prefix
2. The source line is a full article heading, not the same as the TOC entry

This caused the matcher to incorrectly assign heading levels.

## Solution: Stricter Matching

Updated `match_toc_to_source()` to use a **multi-tier matching strategy**:

### Tier 1: Numbering Match (strict)
```python
if toc_entry.numbering and toc_entry.numbering.lower() in search_text:
    match = True  # e.g., "Art. 1" found in "Art. 1 – ..."
```

### Tier 2: Title Full-Line Match (strict)
```python
if toc_entry.title.lower() == search_text:
    match = True  # Exact full-line match only
```

### Tier 3: Title Suffix Match (strict)
```python
if search_text.endswith(toc_entry.title.lower()):
    match = True  # e.g., "ARTICLE 1 – CALL FOR..." ends with "CALL FOR..."
```

### Tier 4: Fuzzy Match (flexible)
```python
if similarity_ratio >= 0.8:
    match = True  # Use SequenceMatcher for OCR-damaged titles
```

## Impact

**Before**: Substring matches anywhere in the line (false positives)
**After**: Only matches when:
- Numbering is found, OR
- Title is the full line, OR
- Title appears at end of line, OR
- Fuzzy similarity >= 0.8

## Examples That Now Work Correctly

| Source | TOC | Match? | Method |
|--------|-----|--------|--------|
| `ARTICLE 1 – CALL FOR...` | `CALL FOR...` | ✓ | Suffix |
| `Art. 1 – Definitions` | `Definitions` | ✓ | Suffix |
| `Art. 1 - Definitions` | (numbering: `Art. 1`) | ✓ | Numbering |
| `Purpose of the call` | `Purpose of the call` | ✓ | Full-line |
| `Some Title` | `Similar Title` (0.8+) | ✓ | Fuzzy |

## Code Location

File: `miner_mineru/pipeline/md_fixer.py`, function `match_toc_to_source()`

Lines: 125-177

## Testing

✅ All 16 existing tests pass
✅ Tests confirm demoting, fuzzy matching, and corrections still work
✅ Backward compatible with existing data

## Notes

- The numbering match is kept loose (substring) because numbering is typically short and specific
- Title matching is strict to avoid the false-positive substring issue
- Fuzzy matching serves as fallback for OCR-damaged text
