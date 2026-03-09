# Miner-MinerU Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-06

## Active Technologies
- Python 3.11+ (conda `agent` environment) + `json` (stdlib), `difflib` (stdlib for fuzzy matching), `os`/`pathlib` (stdlib) (002-fix-source-markdown)
- File-based — reads source `.md` + output `.json`, writes corrected `.md` + report `.json` to `output/fixed/` (002-fix-source-markdown)

- Python 3.11+ (conda `agent` environment) + Anthropic Claude API (for LLM-based classification), `json` stdlib (002-markdown-summary-extraction)

## Project Structure

```text
miner_mineru/              # Main Python package
  agents/                  # One LLM agent per concern
    boundary_agent.py      # Sliding-window TOC boundary detection
    classifier_agent.py    # TOC entry classification
    summary_agent.py       # Document summary generation
    metadata_agent.py      # Document metadata extraction
  models/                  # Pure data models (no LLM calls)
    document.py            # HeadingEntry, TOCBoundary, DocumentMetadata
    results.py             # ExtractionResult, LogEntry
  pipeline/                # Orchestration and utilities
    extractor.py           # extract_toc() — runs all agents in sequence
    reader.py              # File I/O and content slicing
    heading_map.py         # Nested tree builder
    rule_engine.py         # Rule-based heading classifier
    md_fixer.py            # Markdown fixer: normalize heading levels using extracted TOC
  providers/               # LLM backend abstraction
    factory.py             # build_client() — reads LLM_PROVIDER env var
    anthropic.py           # Anthropic Claude client
    azure.py               # Azure OpenAI wrapper
  cli/
    main.py                # CLI entry point
  __main__.py              # python -m miner_mineru
tests/
  conftest.py              # Shared fixtures (notice_md_path, disco_md_path, bologna_md_path)
  golden/                  # Golden JSON fixtures for integration tests
data/                      # Input documents (one subdir per document)
output/                    # Agent JSON output (gitignored)
.specify/                  # Feature specs (speckit workflow)
```

## Commands

```bash
# Run tests (conda agent env, bypass anyio SSL issue)
PYTHONNOUSERSITE=1 "/c/Users/ERO8OFO/.conda/envs/agent/python.exe" -m pytest -p no:anyio

# Run CLI agent (extract TOC)
python -m miner_mineru extract <markdown_file> --output <output.json>

# Fix markdown heading levels using extracted TOC
python -m miner_mineru fix <source.md> --toc <toc.json> --output-dir <output/fixed>
```

## Code Style

Python 3.11+ (conda `agent` environment): Follow standard conventions

## File Organization Rules

**IMPORTANT**: Keep root directory clean. Follow these rules strictly:

### ✅ Files Allowed in Root
- `README.md` - Main project documentation
- `CLAUDE.md` - Development guidelines (this file)
- `.gitignore` - Git configuration
- `pyproject.toml` / `setup.py` - Package configuration
- `.github/` - GitHub workflows

### ❌ DO NOT Create in Root
- Documentation files (`.md`, `.txt`) → Must go in `docs/` folder
- Analysis reports → Must go in `docs/` or `output/`
- Quick reference guides → Must go in `docs/`
- Implementation guides → Must go in `docs/`
- Feature plans → Must go in `.specify/` folder

### Where Things Go

| Type | Location |
|------|----------|
| Feature specifications | `.specify/` |
| Documentation | `docs/` |
| Test fixtures | `tests/fixtures/` |
| Data files | `data/` |
| Output/results | `output/` |
| Code | `miner_mineru/` |
| Tests | `tests/` |

### Current Root Cleanup
These files should be moved to `docs/`:
- `BATCH_INFERENCE_QUICK_START.md` → `docs/`
- `COST_OPTIMIZATION_SUMMARY.md` → `docs/`
- `MATCHING_IMPROVEMENTS.md` → `docs/`
- `NUMBERING_PRIORITY_MATCHING.md` → `docs/`
- `SESSION_CHANGES_SUMMARY.md` → `docs/`
- `STRATEGY_CHANGE_DEMOTING.md` → `docs/`
- `JSON_DOCS.md` → `docs/INDEX.md` (or keep only if it's the main index)

## Recent Changes
- 002-fix-source-markdown: Added Python 3.11+ (conda `agent` environment) + `json` (stdlib), `difflib` (stdlib for fuzzy matching), `os`/`pathlib` (stdlib)

- 002-markdown-summary-extraction: Added Python 3.11+ (conda `agent` environment) + Anthropic Claude API (for LLM-based classification), `json` stdlib

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
