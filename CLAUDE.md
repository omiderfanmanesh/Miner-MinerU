# Miner-MinerU Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-06

## Active Technologies

- Python 3.11+ (conda `agent` environment) + Anthropic Claude API (for LLM-based classification), `json` stdlib (002-markdown-summary-extraction)

## Project Structure

```text
scripts/          # Core library + CLI
  models.py           # Dataclasses: HeadingEntry, TOCBoundary, ExtractionResult, etc.
  toc_extractor.py    # find_toc_boundaries(), classify_toc_entries(), extract_toc()
  toc_extraction_agent.py  # CLI entry point
  llm_client.py       # build_client() — Anthropic or Azure OpenAI
  rule_engine.py      # Rule-based heading helpers
rules/            # Rule modules (annex, article, section, etc.)
tests/            # pytest tests
  conftest.py         # Shared fixtures (notice_md_path, disco_md_path, bologna_md_path)
  golden/             # Golden JSON fixtures for integration tests
data/             # Input documents (MinerU-generated markdown per named subdir)
output/           # Agent JSON output (gitignored)
.specify/         # Feature specs (speckit workflow)
```

## Commands

```bash
# Run tests (conda agent env, bypass anyio SSL issue)
PYTHONNOUSERSITE=1 "/c/Users/ERO8OFO/.conda/envs/agent/python.exe" -m pytest -p no:anyio

# Run CLI agent
python -m scripts.toc_extraction_agent <markdown_file> --output <output.json>
```

## Code Style

Python 3.11+ (conda `agent` environment): Follow standard conventions

## Recent Changes

- 002-markdown-summary-extraction: Added Python 3.11+ (conda `agent` environment) + Anthropic Claude API (for LLM-based classification), `json` stdlib

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
