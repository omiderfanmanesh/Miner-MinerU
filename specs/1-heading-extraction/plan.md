# Implementation Plan: Robust Heading Extraction

**Branch**: `1-heading-extraction` | **Date**: 2026-02-26 | **Spec**: `spec.md`
**Input**: Feature specification from `/specs/1-heading-extraction/spec.md`

## Summary

Implement a deterministic, rule-based pipeline that converts `MinerU_simplified.json` into
structured outputs: `clean.md`, `doc_tree.json`, `pageIndex.json`, and `report.json`.
The pipeline will follow strictly separated stages (ingest → classify → extract → build → render → report),
use only deterministic rule-plugins and logging, and preserve unknown headings.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: Python standard library (re, json, collections); optional: `beautifulsoup4` for HTML table normalization (opt-in).  
**Storage**: Files under `data/.../structure_outputs` (JSON + Markdown).  
**Testing**: `pytest` for unit and integration tests.  
**Target Platform**: Cross-platform (Windows, Linux, macOS).  
**Project Type**: CLI tool + small library (`scripts/structure_pipeline.py` already present).  
**Performance Goals**: Deterministic single-document processing; typical run time under a few seconds for documents of this size.  
**Constraints**: No external network calls; deterministic logic only; preserve all input order and content.  
**Scale/Scope**: Single-document pipeline; batch support optional.

## Constitution Check

GATE: The project follows the repository constitution (library-first, CLI interface, test-first). No violations detected; proceed with Phase 0 research.

## Project Structure

Documentation (this feature)

```text
specs/1-heading-extraction/
├── plan.md              # This file (this implementation plan)
├── research.md          # Phase 0 output (to produce)
├── data-model.md        # Phase 1 output (to produce)
├── quickstart.md        # Phase 1 output (to produce)
└── contracts/           # Phase 1 output (to produce)
```

Source code

```text
scripts/structure_pipeline.py    # deterministic pipeline (exists)
scripts/simplify_pdf_json.py     # simplified JSON generator (exists)
tests/                           # unit and integration tests (to add)
```

**Structure Decision**: Keep pipeline and helpers under `scripts/` for now; if growth demands, move into `src/` as a proper package.

## Phase 0: Outline & Research

1. Resolve any remaining unknowns in Technical Context (e.g., decide whether to require `beautifulsoup4` for table HTML sanitization).  
2. Produce `research.md` capturing rule design, examples for each heading pattern, and mapping decisions.  
3. Create a small corpus of annotated examples to validate numeric-parent resolution and topic attachments.

Output: `research.md` (Phase 0)

## Phase 1: Design & Contracts

1. Create `data-model.md` describing `HeadingNode`, `DocumentItem` and report schema.  
2. Produce `quickstart.md` showing CLI usage: `python scripts/structure_pipeline.py --input <file> --outdir <dir>`.  
3. Add contract examples for `doc_tree.json` and `pageIndex.json`.

Output: `data-model.md`, `contracts/`, `quickstart.md`

## Phase 2: Implementation

1. Implement rule-plugin modules for: ArticleRule, DecimalRule, SectionRule, AnnexRule, CapsTopicRule, TableRule.  
2. Harden `structure_pipeline.py` to load plugins, produce deterministic report items, and include unit tests.  
3. Add integration tests running the pipeline on `MinerU_simplified.json` and comparing structural invariants.

## Phase 3: Polish & Delivery

1. Add more test cases and golden outputs.  
2. Add a small CLI and README quickstart.  
3. Tag release and update spec with results.

## Complexity Tracking

No constitution violations. Key risks: handling malformed numbering and multi-line headings; mitigations: conservative heuristics, logging, and never dropping unknowns.

