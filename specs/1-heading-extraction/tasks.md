# Tasks: Robust Heading Extraction (1-heading-extraction)

**Input**: Design documents from `specs/1-heading-extraction/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md` (research.md may be created during Phase 0)

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Create Python CLI entrypoint `scripts/structure_pipeline.py` (ensure `--input` and `--outdir` args) — `scripts/structure_pipeline.py`
- [ ] T002 Initialize test harness and requirements file `tests/requirements.txt` — `tests/requirements.txt`
- [ ] T003 [P] Add `pytest` configuration and CI job stub `pyproject.toml` and `.github/workflows/ci.yml` — `pyproject.toml`, `.github/workflows/ci.yml`

---

## Phase 2: Foundational (Blocking Prerequisites)

- [ ] T004 Implement `data-model.md` describing `HeadingNode`, `DocumentItem`, `Report` schemas — `specs/1-heading-extraction/data-model.md`
- [ ] T005 [P] Create `research.md` capturing rule designs, examples, and mapping decisions — `specs/1-heading-extraction/research.md`
- [ ] T006 [P] Add golden sample fixtures (annotated headings) for tests — `tests/fixtures/golden/*.json`
- [ ] T007 Implement logging/report scaffold `scripts/reporting.py` used by pipeline to append deterministic events — `scripts/reporting.py`

---

## Phase 3: User Story 1 - Convert document to structured tree (Priority: P1) 🎯 MVP

**Goal**: Deterministic rule-based heading extraction, numeric-parent resolution, and `doc_tree.json` output.

### Implementation

- [ ] T008 [US1] Create rule-plugin skeletons: `rules/article.py`, `rules/decimal.py`, `rules/section.py`, `rules/annex.py`, `rules/capstopic.py` — `rules/`
- [ ] T009 [US1] Implement `rules/decimal.py` parsing dotted numbering and returning numeric segments — `rules/decimal.py`
- [ ] T010 [US1] Implement `rules/article.py` to detect `ART`/`Art` patterns and normalize to `Art. N` — `rules/article.py`
- [ ] T011 [US1] Implement `rules/capstopic.py` detecting short ALL-CAPS topics (length 6–60, low punctuation) — `rules/capstopic.py`
- [ ] T012 [US1] Integrate plugins into `scripts/structure_pipeline.py` (classification stage) — `scripts/structure_pipeline.py`
- [ ] T013 [US1] Implement numeric-parent resolution (longest-prefix match) in `scripts/tree_builder.py` — `scripts/tree_builder.py`
- [ ] T014 [US1] Add unit tests for numeric-parent resolution using golden fixtures — `tests/unit/test_tree_builder.py`
- [ ] T015 [US1] Ensure unknown headings are preserved as `unknown` nodes and logged — `scripts/structure_pipeline.py`
- [ ] T016 [US1] Produce `doc_tree.json` with `HeadingNode` schema — `data/.../structure_outputs/doc_tree.json`

### Acceptance tests

- [ ] T017 [US1] Integration test: run pipeline on `data/.../MinerU_simplified.json` and assert `Art.10` normalized and `2.2.1` nested correctly — `tests/integration/test_pipeline_mineru.py`

---

## Phase 4: User Story 2 - Preserve tables and page mapping (Priority: P2)

**Goal**: Retain table HTML in node content and create page→heading index.

- [ ] T018 [US2] Implement `rules/table.py` to tag table items and preserve `html` in `content` entries — `rules/table.py`
- [ ] T019 [US2] Enhance pipeline to populate `pageIndex.json` mapping page → heading ids/titles — `scripts/structure_pipeline.py`
- [ ] T020 [US2] Integration test verifying table HTML appears under nearest heading `content` — `tests/integration/test_tables_and_pages.py`

---

## Phase 5: User Story 3 - Explain decisions (Priority: P2)

**Goal**: Full audit trail into `report.json` with rule usage counts and unknowns.

- [ ] T021 [US3] Implement per-item classification logging into `report.json` (include rules tried, scores, final decision) — `scripts/reporting.py`
- [ ] T022 [US3] Aggregate rule usage counters and unknown headings into `report.json` — `scripts/reporting.py`
- [ ] T023 [US3] Add tests ensuring `report.json` contains `unknown_headings` and `unmatched_numeric_prefix` entries for malformed cases — `tests/unit/test_reporting.py`

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T024 [P] Add CLI docs and quickstart `specs/1-heading-extraction/quickstart.md` and `README.md` — `specs/1-heading-extraction/quickstart.md`, `README.md`
- [ ] T025 [P] Add packaging or `src/` reorg if library growth demands — repo reorg (advisory)
- [ ] T026 [P] Performance/robustness: add timeout/streaming strategy for very large documents — `scripts/structure_pipeline.py`

---

## Dependencies & Execution Order

- Setup (Phase 1) must complete before Foundational (Phase 2).  
- Foundational (Phase 2) must complete before User Stories (P1/P2/P3).  
- User Story tasks may run in parallel when marked `[P]`.

## Parallel Execution Examples

- Run T009, T010, T011 in parallel (each rule implementation is independent) — they modify files under `rules/`.
- Run T018 and T019 in parallel once classification is stable.

## Implementation Strategy

- MVP: Deliver Phase 1–3 (through T017) first to produce a working `doc_tree.json` and basic `report.json`.  
- Then deliver Phase 4–5 to capture tables and full auditability.  
- Tests: Unit tests for each rule and integration tests on `MinerU_simplified.json` are required before merge.
