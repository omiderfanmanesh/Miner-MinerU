"""Markdown fixing use case."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from collections import Counter
from contextlib import nullcontext
from math import ceil

from docstruct.application.agents.llm_heading_matcher import LLMHeadingMatcher
from docstruct.domain.heading_matcher import (
    _collect_llm_candidate_lines,
    match_toc_patterns_exactly,
    match_toc_to_source,
    match_toc_with_llm_fallback,
)
from docstruct.domain.level_mapper import (
    apply_all_corrections,
    apply_heading_level,
    find_first_toc_match_index,
    kind_to_heading_level,
)
from docstruct.domain.models import CorrectionReport, SourceLine, TOCEntry
from docstruct.infrastructure.file_io import (
    parse_source_markdown,
    write_correction_report,
    write_corrected_markdown,
)
from docstruct.infrastructure.llm.factory import build_client
from tqdm import tqdm


def _verbose_log(enabled: bool, message: str) -> None:
    if enabled:
        print(f"INFO: {message}", file=sys.stderr)


def _terminal_log(message: str) -> None:
    tqdm.write(f"INFO: {message}", file=sys.stderr)


def _progress_enabled(show_progress: bool | None) -> bool:
    if show_progress is not None:
        return show_progress
    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()


def _progress_bar(total: int, desc: str, enabled: bool):
    if total <= 0:
        return nullcontext(None)
    return tqdm(
        total=total,
        desc=desc,
        unit="step",
        file=sys.stderr,
        dynamic_ncols=True,
        leave=False,
        disable=not enabled,
    )


def _log_duplicate_heading_matches(matched_pairs: dict[int, TOCEntry]) -> None:
    heading_counts = Counter(
        entry.heading_pattern() or entry.title
        for entry in matched_pairs.values()
        if (entry.heading_pattern() or entry.title)
    )
    for heading_text, count in sorted(heading_counts.items()):
        if count > 1:
            _terminal_log(f'Heading "{heading_text}" found {count} times in the document; fixing all occurrences.')


def load_toc_from_json(toc_json_path: str) -> tuple[list[TOCEntry], tuple[int, int] | None]:
    with open(toc_json_path, encoding="utf-8") as handle:
        data = json.load(handle)

    toc_entries = [
        TOCEntry(
            title=entry["title"],
            kind=entry["kind"],
            depth=entry["depth"],
            numbering=entry.get("numbering"),
            separator=entry.get("separator"),
            pattern=entry.get("pattern"),
            page=entry.get("page"),
            confidence=entry.get("confidence", 1.0),
        )
        for entry in data.get("toc", [])
    ]

    toc_section_range = None
    boundaries = data.get("toc_boundaries", {})
    if boundaries.get("start_line") is not None and boundaries.get("end_line") is not None:
        toc_section_range = (int(boundaries["start_line"]), int(boundaries["end_line"]))
    return toc_entries, toc_section_range


def build_correction_report(
    source_path: str,
    output_path: str,
    source_lines: list[SourceLine],
    corrections,
    unmatched_toc: list[str],
) -> CorrectionReport:
    lines_changed = sum(
        1
        for correction in corrections
        if correction.old_level != correction.new_level or (correction.old_level and not correction.new_level)
    )
    lines_demoted = sum(1 for correction in corrections if correction.match_method == "demoted")
    return CorrectionReport(
        source_file=source_path,
        output_file=output_path,
        total_lines=len(source_lines),
        lines_changed=lines_changed,
        lines_demoted=lines_demoted,
        unmatched_toc_entries=unmatched_toc,
        corrections=corrections,
    )


def fix_markdown(
    source_path: str,
    toc_json_path: str,
    output_dir: str,
    report_dir: str | None = None,
    use_llm_matching: bool = True,
    verbose: bool = False,
    show_progress: bool | None = None,
) -> CorrectionReport:
    toc_entries, toc_section_range = load_toc_from_json(toc_json_path)
    source_lines = parse_source_markdown(source_path)
    progress_enabled = _progress_enabled(show_progress)
    _verbose_log(verbose, f"Loaded {len(toc_entries)} TOC entries from {toc_json_path}")
    _verbose_log(verbose, f"Parsed {len(source_lines)} source lines from {source_path}")

    with _progress_bar(len(toc_entries), "Exact heading match", progress_enabled) as exact_progress:
        source_lines, matched_pairs, unmatched_entries, match_methods = match_toc_patterns_exactly(
            toc_entries,
            source_lines,
            toc_section_range,
            verbose=verbose,
            progress_bar=exact_progress,
        )
    _verbose_log(verbose, f"Exact matching finished: {len(matched_pairs)} matched, {len(unmatched_entries)} unmatched")

    if use_llm_matching and unmatched_entries:
        try:
            _terminal_log(f"Using LLM fallback for {len(unmatched_entries)} unmatched TOC entries.")
            matcher = LLMHeadingMatcher(build_client())
            llm_candidates = _collect_llm_candidate_lines(
                source_lines,
                unmatched_entries,
                matched_pairs,
                toc_section_range,
            )
            llm_steps = ceil(len(llm_candidates) / matcher._BATCH_SIZE)
            with _progress_bar(llm_steps, "LLM heading match", progress_enabled) as llm_progress:
                source_lines, llm_matches, unmatched_entries, llm_methods = match_toc_with_llm_fallback(
                    unmatched_entries,
                    source_lines,
                    matched_pairs,
                    toc_section_range,
                    matcher,
                    verbose=verbose,
                    progress_bar=llm_progress,
                )
            matched_pairs.update(llm_matches)
            match_methods.update(llm_methods)
            _terminal_log(f"LLM fallback matched {len(llm_matches)} additional heading occurrences.")
            _verbose_log(verbose, f"LLM fallback finished: {len(llm_matches)} additional matches, {len(unmatched_entries)} still unmatched")
        except Exception as exc:  # pragma: no cover
            print(f"WARNING: LLM fallback skipped: {exc}", file=sys.stderr)
    elif not unmatched_entries:
        _verbose_log(verbose, "All TOC entries matched exactly; LLM fallback not needed")
    else:
        _verbose_log(verbose, "LLM fallback disabled; leaving unmatched TOC entries in the report")

    with _progress_bar(len(source_lines), "Apply heading fixes", progress_enabled) as correction_progress:
        corrected_lines, corrections = apply_all_corrections(
            source_lines,
            matched_pairs,
            toc_entries,
            match_methods=match_methods,
            progress_bar=correction_progress,
        )
    _log_duplicate_heading_matches(matched_pairs)

    source_filename = Path(source_path).name
    corrected_path = str(Path(output_dir) / source_filename)
    report_output_dir = Path(report_dir) if report_dir else Path(output_dir)
    report_path = str(report_output_dir / f"{Path(source_filename).stem}_report.json")

    write_corrected_markdown(corrected_lines, corrected_path)
    report = build_correction_report(
        source_path,
        corrected_path,
        source_lines,
        corrections,
        [entry.title for entry in unmatched_entries],
    )
    write_correction_report(report, report_path)
    return report


__all__ = [
    "apply_all_corrections",
    "apply_heading_level",
    "build_correction_report",
    "find_first_toc_match_index",
    "fix_markdown",
    "kind_to_heading_level",
    "load_toc_from_json",
    "match_toc_to_source",
]
