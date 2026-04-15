"""Chunked Markdown normalization using a local Ollama model."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
import re
import sys

from tqdm import tqdm

from docstruct.application.ports import LLMPort
from docstruct.domain.models import NormalizationChunk, NormalizationReport
from docstruct.infrastructure.llm.ollama_adapter import OllamaAdapter

_ARTICLE_LINE_RE = re.compile(
    r"^(?:#+\s*)?(?:art(?:icle|icolo)?\.?\s*\d+[a-z]?|chapter\s+[ivxlcdm\d]+|section\s+\d+|\d+(?:\.\d+)+)\b",
    re.IGNORECASE,
)
_HEADING_RE = re.compile(r"^#{1,6}\s+.+$")

_SYSTEM_PROMPT = """You normalize noisy markdown extracted from formal documents.

Return only normalized markdown for the provided chunk.

Rules:
- Preserve the source language and substantive meaning.
- Do not summarize, omit facts, or invent content.
- Normalize article and subarticle headings into markdown headings when they are clearly headings.
- Prefer:
  - `#` for major document sections or chapter-like headings
  - `##` for article headings
  - `###` for subarticle headings such as `1.1`, `2.3`, `Art. 4.1`, or similar
- Remove obvious extraction noise such as isolated page numbers, repeated headers/footers, and standalone image placeholders.
- Fix obvious spacing, punctuation, and numbering corruption only when the correction is strongly supported by the local text.
- Keep lists, tables, and paragraphs as markdown.
- This chunk may begin or end mid-document, so do not add missing context from outside the chunk.
"""


@dataclass
class _MarkdownChunk:
    index: int
    start_line: int
    end_line: int
    text: str


def _looks_like_boundary(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith("#"):
        return True
    return bool(_ARTICLE_LINE_RE.match(stripped))


def split_markdown_into_chunks(markdown_text: str, *, chunk_size: int = 6000) -> list[_MarkdownChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    lines = markdown_text.splitlines()
    if not lines:
        return []

    chunks: list[_MarkdownChunk] = []
    buffer: list[str] = []
    start_line = 1
    buffer_chars = 0
    in_fence = False

    def flush(end_line: int) -> None:
        nonlocal buffer, start_line, buffer_chars
        if not buffer:
            return
        chunks.append(
            _MarkdownChunk(
                index=len(chunks) + 1,
                start_line=start_line,
                end_line=end_line,
                text="\n".join(buffer).strip("\n"),
            )
        )
        buffer = []
        buffer_chars = 0

    for line_number, line in enumerate(lines, start=1):
        if buffer and not in_fence and buffer_chars >= chunk_size and _looks_like_boundary(line):
            flush(line_number - 1)
            start_line = line_number

        buffer.append(line)
        buffer_chars += len(line) + 1

        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence

    flush(len(lines))
    return chunks


def _strip_response_wrapper(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return cleaned


def _extract_recent_headings(markdown_text: str, *, limit: int = 4) -> list[str]:
    headings = [line.strip() for line in markdown_text.splitlines() if _HEADING_RE.match(line.strip())]
    if limit <= 0:
        return []
    return headings[-limit:]


def _build_messages(chunk: _MarkdownChunk, recent_headings: list[str]) -> list[dict]:
    context_block = "\n".join(recent_headings) if recent_headings else "(none)"
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Recent normalized heading context from earlier chunks:\n"
                f"{context_block}\n\n"
                f"Normalize chunk {chunk.index} covering source lines {chunk.start_line}-{chunk.end_line}.\n"
                "Return only markdown.\n\n"
                "Chunk:\n"
                f"{chunk.text}"
            ),
        },
    ]


def _write_report(report: NormalizationReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


def _progress_enabled(show_progress: bool | None) -> bool:
    if show_progress is not None:
        return show_progress
    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()


def normalize_markdown(
    source_path: str,
    output_dir: str,
    *,
    report_dir: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    chunk_size: int = 6000,
    max_tokens: int = 2048,
    show_progress: bool | None = None,
    client: LLMPort | None = None,
) -> NormalizationReport:
    input_path = Path(source_path)
    if not input_path.exists():
        raise FileNotFoundError(source_path)

    markdown_text = input_path.read_text(encoding="utf-8")
    chunks = split_markdown_into_chunks(markdown_text, chunk_size=chunk_size)
    selected_model = (model or os.getenv("OLLAMA_MODEL") or "gemma4").strip()
    llm_client = client or OllamaAdapter(base_url=base_url or os.getenv("OLLAMA_BASE_URL"))

    normalized_parts: list[str] = []
    report_chunks: list[NormalizationChunk] = []
    recent_headings: list[str] = []

    iterator = tqdm(chunks, desc="Normalize markdown", unit="chunk", disable=not _progress_enabled(show_progress))
    for chunk in iterator:
        response = llm_client.create_message(
            model=selected_model,
            max_tokens=max_tokens,
            messages=_build_messages(chunk, recent_headings),
        )
        normalized_text = _strip_response_wrapper(response)
        if not normalized_text:
            normalized_text = chunk.text
        normalized_parts.append(normalized_text)
        recent_headings = _extract_recent_headings("\n".join([*recent_headings, normalized_text]))
        report_chunks.append(
            NormalizationChunk(
                index=chunk.index,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                input_chars=len(chunk.text),
                output_chars=len(normalized_text),
            )
        )

    normalized_content = "\n\n".join(part.strip("\n") for part in normalized_parts if part.strip("\n"))
    if normalized_content and not normalized_content.endswith("\n"):
        normalized_content += "\n"

    output_path = Path(output_dir) / input_path.name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(normalized_content, encoding="utf-8")

    report_output_dir = Path(report_dir) if report_dir else Path(output_dir)
    report = NormalizationReport(
        source_file=str(input_path),
        output_file=str(output_path),
        model=selected_model,
        chunk_count=len(report_chunks),
        chunks=report_chunks,
    )
    _write_report(report, report_output_dir / f"{input_path.stem}_normalize_report.json")
    return report


__all__ = ["normalize_markdown", "split_markdown_into_chunks"]
