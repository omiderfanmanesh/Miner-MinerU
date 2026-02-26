# Feature Specification: Robust Heading Extraction for Arbitrary Legal PDFs

**Feature Branch**: `001-heading-extraction`  
**Created**: 2026-02-26  
**Status**: Draft  
**Input**: User description: "Robust multi-format heading extraction and tree builder"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Convert document to structured tree (Priority: P1)

A user provides the `MinerU_simplified.json` for a legal PDF and needs a deterministic hierarchical representation (articles, subsections, sections, annexes, topics) so that downstream tooling (search, display, citations) can consume it.

Why this priority: This is the primary value: structured navigation and programmatic access.  
Independent Test: Run the pipeline on a sample input and validate `doc_tree.json` contains expected numbering and parent relationships for known examples.

Acceptance Scenarios:
1. Given a PDF with `Art. 10` and `2.2.1` sections, when the pipeline runs, then `Art. 10` is normalized to `Art. 10` and `2.2.1` is nested under `2.2` and parent resolution follows longest-prefix matching.
2. Given a CAPS heading `SPECIAL CASES`, when processed, then it appears as a `topic` node preserved in the tree and attached to the nearest structural parent.

---

### User Story 2 - Preserve tables and page mapping (Priority: P2)

The user needs table HTML retained in node content and a page→heading index for rendering and page-level navigation.

Why this priority: Tables and page mapping are necessary for correct rendering and referencing.  
Independent Test: `pageIndex.json` contains page keys mapping to the heading ids/titles that appear on those pages; `doc_tree.json` nodes include `content` entries for tables with original HTML preserved.

Acceptance Scenario:
1. Given a table block with `html` in simplified JSON, when processed, then the table's HTML is present under the nearest heading's `content` as kind `table`.

---

### User Story 3 - Explain decisions (Priority: P2)

Operators must be able to audit why a line was classified as a heading and understand ambiguous assignments.

Why this priority: For legal documents, traceability is required; deterministic logging prevents silent data loss.  
Independent Test: `report.json` records rule matches, counts per rule, unknown headings, unmatched numeric prefixes, and ambiguous assignment warnings.

Acceptance Scenario:
1. When an unknown short heading is encountered, it is included in `report.json` under `unknown_headings` with the original text and index.

### Edge Cases

- Multi-line headings where numbering and title are split across adjacent items: prefer concatenation when both items are short and one is numeric.  
- Malformed numbering (e.g., missing dots or duplicated numbers) should be preserved and logged as `unmatched_numeric_prefix`.  
- Page numbers embedded in titles (e.g., "2.1 Title ........ 12") should be extracted as page when trailing integer matches TOC-like separation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Pipeline MUST ingest `MinerU_simplified.json` and process items in original order without LLMs.
- **FR-002**: Pipeline MUST classify items into kinds: `article`, `subsection`, `section`, `annex`, `topic`, `paragraph`, `table`, `image`, `page_number`, `unknown` using rule plugins and deterministic scoring.
- **FR-003**: For dotted numbering (e.g., `2.2.1`), pipeline MUST parse numeric segments and use longest-prefix match to select parent (numeric hierarchy principle).
- **FR-004**: Pipeline MUST attach unnumbered ALL-CAPS short lines as `topic` and attach to nearest structural parent (subsection > article > section); record the decision.
- **FR-005**: Table `html` content MUST be preserved in node `content` as kind `table`.
- **FR-006**: Unknown headings MUST be preserved as nodes of type `unknown` and listed in `report.json`.
- **FR-007**: Pipeline MUST produce the following outputs in `structure_outputs`: `clean.md`, `doc_tree.json`, `pageIndex.json`, `report.json`.
- **FR-008**: All classification decisions, rule matches, and counts MUST be logged to `report.json` for auditability.
- **FR-009**: Pipeline MUST be deterministic: same input → same outputs. No randomness, no external calls.
- **FR-010**: Parent resolution MUST attach decimal headings to an article when the first numeric segment equals an article number (if present).

- **FR-011**: Heading level rendering MUST follow the agreed mapping: Section → H1; Article → H2; Decimal subsections → dynamic headings starting at H3 based on depth; Topic (short ALL-CAPS) → H4; Annex → H1. This mapping is deterministic and MUST be applied when producing `clean.md`.

### Key Entities

- **DocumentItem**: a single item from `MinerU_simplified.json` with `type` and `text`.
- **RulePlugin**: deterministic rule that inspects an item and emits a score and candidate kind (e.g., ArticleRule, DecimalRule, SectionRule, CapsTopicRule).
- **HeadingNode**: structured node in `doc_tree.json` with `id`, `numbering?`, `title`, `depth`, `kind`, `page?`, `content[]`, `children[]`.
- **Report**: audit object capturing per-item classification, rule usage counts, unknown headings, unresolved prefixes, and warnings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `Art.10` must appear as `Art. 10` (normalized) in `doc_tree.json` and `clean.md` for the provided corpus examples.
- **SC-002**: For a sample set of 100 known headings (including nested decimal variants), at least 98% of numeric-parent relationships must match expected longest-prefix resolution.
- **SC-003**: `report.json` MUST list all `unknown` headings (0 tolerated omissions) and rule usage counts; unknowns must be ≤ 5% of headings for typical well-formed legal PDFs.
- **SC-004**: Pipeline run time shall be deterministic and repeatable on the same environment (identical outputs); any nondeterminism must be documented as a bug.

## Assumptions

- Input `MinerU_simplified.json` preserves reading order and page numbers (if detected).  
- Table `html` is stored in span `html` and was already extracted into `text` by the simplified JSON generator.  
- No external network calls are permitted during parsing.

## Success Criteria Validation

Provide a small test harness (separate task) that runs the pipeline on a curated set of examples and compares `doc_tree.json` against golden outputs.

**End of spec**

## Clarifications

### Session 2026-02-26
- Q: Heading level mapping for rendering → A: Option A - Section → H1; Article → H2; Subsection → dynamic H3+ by depth; Topic → H4; Annex → H1
