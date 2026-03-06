# MinerU Pipeline Usage Guide

## Overview

The MinerU pipeline consists of two main steps:

1. **Extract TOC** (Feature 001): Extract table of contents from markdown using LLM
2. **Fix Markdown** (Feature 002): Normalize heading levels using the extracted TOC

## Quick Start

### Step 1: Extract TOC from a Single File

```bash
python -m miner_mineru extract <markdown_file> --output output/<name>.json
```

Example:
```bash
python -m miner_mineru extract data/notice.md --output output/notice_toc.json
```

**Requirements:**
- Anthropic API key in `ANTHROPIC_API_KEY` environment variable
- OR Azure OpenAI credentials with `LLM_PROVIDER=azure` environment variable

### Step 2: Fix Heading Levels

```bash
python -m miner_mineru fix <markdown_file> --toc <toc.json> --output-dir output/fixed
```

Example:
```bash
python -m miner_mineru fix data/notice.md --toc output/notice_toc.json --output-dir output/fixed
```

**Output:**
- `output/fixed/<filename>.md` - Corrected markdown with normalized heading levels
- `output/fixed/<filename>_report.json` - Detailed correction report

## Batch Processing

### Fixer Batch Script (No LLM Required)

```bash
python run_fixer.py
```

This script:
- Finds all markdown files in `./data`
- Looks for matching extracted TOC JSON files in `./output`
- Automatically fixes all matched pairs
- Generates corrected markdown + reports in `output/fixed/`

No LLM provider setup needed!

## Pipeline Architecture

### Feature 001: TOC Extraction
- **Module**: `miner_mineru/agents/`, `miner_mineru/pipeline/extractor.py`
- **Input**: Markdown file
- **Output**: JSON with TOC entries (title, kind, depth, numbering, page)
- **Entry Point**: `python -m miner_mineru extract`

### Feature 002: Markdown Fixer
- **Module**: `miner_mineru/pipeline/md_fixer.py`
- **Input**: Markdown file + extracted TOC JSON
- **Output**: Corrected markdown + correction report JSON
- **Entry Point**: `python -m miner_mineru fix`

## Heading Level Mapping

The fixer normalizes heading levels based on TOC entry `kind`:

| Kind | Level | Markdown |
|------|-------|----------|
| section, annex | H1 | # |
| article | H2 | ## |
| subarticle, subsection | H3 | ### |
| topic | H4 | #### |

## Matching Strategies

The fixer uses multiple strategies to match TOC entries to source headings:

1. **Exact Match**: Numbering or title found as substring in source
2. **Fuzzy Match**: Title similarity ≥ 80% (difflib.SequenceMatcher)
3. **Inferred**: Pattern-based detection for unmatched headings
   - `SECTION I`, `SECTION II`, etc. → H1
   - `ART. X`, `ARTICLE X` → H2
   - `ART. X(Y)`, `ART. X(Y.Z)` → H3
4. **Demoted**: Heading removed (cover page junk before first TOC match)

## Correction Report

Each fixed file generates a JSON report with:

```json
{
  "source_file": "...",
  "output_file": "...",
  "total_lines": 5022,
  "lines_changed": 252,
  "lines_demoted": 1,
  "unmatched_toc_entries": ["item 1", "item 2"],
  "corrections": [
    {
      "line_number": 72,
      "old_level": 1,
      "new_level": 2,
      "matched_toc_title": "Article 1",
      "match_method": "exact"
    }
  ]
}
```

**Match Methods:**
- `exact`: Numbering/title exactly matched
- `fuzzy`: Title fuzzy-matched with 80%+ similarity
- `inferred`: Heading level inferred from SECTION/ART text patterns
- `demoted`: Heading marker removed (cover page)

## Environment Setup

### Python Environment
```bash
conda activate agent
```

### API Keys (for TOC extraction)

**Anthropic (default):**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python -m miner_mineru extract <file>
```

**Azure OpenAI:**
```bash
export LLM_PROVIDER=azure
export AZURE_OPENAI_API_KEY=...
export AZURE_OPENAI_ENDPOINT=...
export AZURE_OPENAI_DEPLOYMENT=...
export AZURE_OPENAI_API_VERSION=...
python -m miner_mineru extract <file>
```

## Testing

Run the test suite:

```bash
PYTHONNOUSERSITE=1 python -m pytest tests/ -p no:anyio -v
```

Run only fixer tests:

```bash
PYTHONNOUSERSITE=1 python -m pytest tests/test_md_fixer.py -p no:anyio -v
```

## File Structure

```
miner_mineru/
  agents/              # LLM agents for extraction
  models/              # Data models
  pipeline/
    md_fixer.py        # Heading normalization logic
    extractor.py       # TOC extraction orchestration
  cli/
    main.py            # CLI entry point (extract + fix commands)
  providers/           # LLM provider abstraction

data/                  # Input markdown files
output/                # Extracted TOC JSON files
output/fixed/          # Corrected markdown + reports
run_fixer.py           # Batch fixer script (no LLM needed)
```

## Examples

### Example 1: Single File Pipeline

```bash
# Extract TOC
python -m miner_mineru extract data/notice.md --output output/notice.json

# Fix headings
python -m miner_mineru fix data/notice.md --toc output/notice.json --output-dir output/fixed

# View corrected file
cat output/fixed/notice.md

# View correction report
cat output/fixed/notice_report.json
```

### Example 2: Batch Process All Files

```bash
# Run fixer on all markdown/TOC pairs
python run_fixer.py

# Results:
# ✓ output/fixed/file1.md
# ✓ output/fixed/file2.md
# ✓ output/fixed/file1_report.json
# ✓ output/fixed/file2_report.json
```

## Troubleshooting

### "No module named 'miner_mineru'"

Make sure you're running from the repository root:
```bash
cd /c/Projects/personal/Miner-MinerU
python -m miner_mineru extract ...
```

### "openai package not installed" (Extract Step)

The extract step requires an LLM provider. Either:

1. Set up Anthropic API:
   ```bash
   export ANTHROPIC_API_KEY=your-key
   python -m miner_mineru extract <file>
   ```

2. Use the fixer batch script (no LLM needed):
   ```bash
   python run_fixer.py
   ```

### Unicode Encoding Errors

On Windows console, the JSON output to stdout may fail due to encoding. The files are still written correctly to disk with UTF-8 encoding. Check:
```bash
cat output/fixed/<filename>.md
```

## Project Status

- ✅ Feature 001: TOC extraction from markdown (16 tests)
- ✅ Feature 002: Markdown fixer with heading normalization (20 tests)
- ✅ Inference patterns for SECTION/ART document structure (4 new tests)
- ✅ Batch processing script (no LLM required)
- **Total**: 55 tests passing

## References

- [CLAUDE.md](CLAUDE.md) - Project guidelines and structure
- [miner_mineru/pipeline/md_fixer.py](miner_mineru/pipeline/md_fixer.py) - Fixer implementation
- [tests/test_md_fixer.py](tests/test_md_fixer.py) - Test suite with usage examples
