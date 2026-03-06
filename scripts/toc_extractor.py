"""TOC extraction library for MinerU-generated markdown files.

Design:
  - find_toc_boundaries(): LLM-based sliding window — agent reads 100-line
    chunks and decides which lines contain TOC content, until it signals done.
  - classify_toc_entries(): LLM-based classification of the detected TOC block.
"""
from __future__ import annotations

import json
import re
import sys

_CHUNK_SIZE = 100  # lines per sliding window chunk


def read_markdown_file(path: str) -> list[str]:
    """Read a markdown file and return its lines. Raises FileNotFoundError if missing."""
    with open(path, encoding="utf-8") as f:
        return f.readlines()


def find_toc_boundaries(lines: list[str], client) -> "TOCBoundary | None":
    """Use an LLM agent to find the TOC section via a sliding 100-line window.

    The agent reads each chunk and returns:
      - toc_start: line offset within chunk where TOC begins (-1 if not started yet)
      - toc_end:   line offset within chunk where TOC ends (-1 if not ended yet)
      - status:    "searching" | "in_toc" | "done"

    Scanning stops when the agent returns status="done" or we run out of lines.
    Only scans the first 600 lines (TOC is always near the start).
    Returns TOCBoundary or None if no TOC found.
    """
    from scripts.models import TOCBoundary

    MAX_LINES = 600
    scan_lines = lines[:MAX_LINES]

    toc_start_abs = None
    toc_end_abs = None
    status = "searching"

    chunk_start = 0
    while chunk_start < len(scan_lines):
        chunk = scan_lines[chunk_start : chunk_start + _CHUNK_SIZE]
        numbered = "".join(
            f"[{chunk_start + i}] {line}" for i, line in enumerate(chunk)
        )

        prompt = (
            "You are scanning a MinerU-extracted markdown document to find the Table of Contents (TOC).\n\n"
            "The TOC may be labeled with a heading like '# Summary', '# TABLE OF CONTENTS', "
            "'# Sommario', '# Indice', or have no heading at all (entries start directly).\n"
            "TOC entries look like: article/section titles with optional page numbers, "
            "decimal numbering (1.1, 2.3), or 'Art. N / Article N' prefixes.\n"
            "Body prose looks like: full sentences, definitions, legal clauses — NOT title listings.\n\n"
            f"Current scan status: {status}\n\n"
            "Below are document lines with their absolute line numbers in [brackets].\n"
            "Analyze this chunk and return a JSON object with:\n"
            '  "toc_start": absolute line number where TOC begins in this chunk, or -1 if TOC has not started yet\n'
            '  "toc_end": absolute line number where TOC ends in this chunk, or -1 if TOC has not ended yet (still continuing)\n'
            '  "status": "searching" (no TOC found yet), "in_toc" (TOC started but not ended), or "done" (TOC ended)\n\n'
            "Rules:\n"
            "- If status was 'in_toc' coming in and TOC continues through this whole chunk: toc_start=-1, toc_end=-1, status='in_toc'\n"
            "- If status was 'in_toc' and TOC ends in this chunk: toc_start=-1, toc_end=<line>, status='done'\n"
            "- If TOC starts and ends in this chunk: set both toc_start and toc_end, status='done'\n"
            "- If TOC starts but does not end: toc_start=<line>, toc_end=-1, status='in_toc'\n"
            "- If no TOC in this chunk: toc_start=-1, toc_end=-1, status='searching'\n"
            "Return ONLY the JSON object, no explanation.\n\n"
            f"CHUNK:\n{numbered}"
        )

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        result = json.loads(raw)
        chunk_status = result.get("status", "searching")
        chunk_toc_start = result.get("toc_start", -1)
        chunk_toc_end = result.get("toc_end", -1)

        print(
            f"INFO: chunk {chunk_start}-{chunk_start+len(chunk)-1}: "
            f"status={chunk_status}, toc_start={chunk_toc_start}, toc_end={chunk_toc_end}",
            file=sys.stderr,
        )

        if toc_start_abs is None and chunk_toc_start >= 0:
            toc_start_abs = chunk_toc_start

        if chunk_toc_end >= 0:
            toc_end_abs = chunk_toc_end

        status = chunk_status
        if status == "done":
            break

        chunk_start += _CHUNK_SIZE

    if toc_start_abs is None:
        return None

    # If TOC never ended (ran out of scan range), use last scanned line
    if toc_end_abs is None:
        toc_end_abs = min(chunk_start + _CHUNK_SIZE, len(lines)) - 1

    # Strip trailing blank lines
    while toc_end_abs > toc_start_abs and not lines[toc_end_abs].strip():
        toc_end_abs -= 1

    return TOCBoundary(
        start_line=toc_start_abs,
        end_line=toc_end_abs,
        marker="(agent-detected)",
    )


def slice_toc_content(lines: list[str], boundary: "TOCBoundary") -> str:
    """Return the raw text of the TOC section as a single string."""
    return "".join(lines[boundary.start_line : boundary.end_line + 1])


def extract_pre_toc_content(lines: list[str], boundary: "TOCBoundary") -> str:
    """Return lines before the TOC start, skipping image lines."""
    pre = [
        line for line in lines[: boundary.start_line]
        if not line.strip().startswith("![image](")
    ]
    return "".join(pre)


def build_heading_map(flat_entries: list["HeadingEntry"]) -> list["HeadingEntry"]:
    """Convert a flat list of HeadingEntry objects into a nested tree by depth."""
    import copy

    roots: list = []
    stack: list = []

    for entry in flat_entries:
        node = copy.copy(entry)
        node.children = []

        while stack and stack[-1].depth >= node.depth:
            stack.pop()

        if stack:
            stack[-1].children.append(node)
        else:
            roots.append(node)

        stack.append(node)

    return roots


def classify_toc_entries(toc_text: str, client) -> list["HeadingEntry"]:
    """Use Claude to classify TOC entries as section/article/subarticle/annex/topic.

    Sends the full TOC text block in a single API call. Returns a list of
    HeadingEntry objects. No regex used — LLM decides classification.
    """
    from scripts.models import HeadingEntry

    prompt = (
        "You are processing a Table of Contents from a MinerU-extracted legal/academic PDF.\n\n"
        "Below is the raw TOC text. Classify EVERY entry (skip the header line itself).\n\n"
        "For each line that is a TOC entry, return a JSON object with:\n"
        '  "title": the heading text (without numbering or page number)\n'
        '  "kind": one of "section", "article", "subarticle", "annex", "topic"\n'
        '  "numbering": the numbering prefix if present (e.g. "Art. 1", "SECTION I", "1.2.3"), else null\n'
        '  "page": the trailing page number as integer if present, else null\n'
        '  "depth": 1 for section, 2 for article, 3+ for subarticle (based on nesting)\n'
        '  "confidence": your confidence 0.0-1.0\n\n'
        "Return ONLY a JSON array of objects, no explanation, no markdown fences.\n\n"
        "Classification rules:\n"
        "- SECTION / SEZIONE / SECTION I-XI → kind=section, depth=1\n"
        "- Art. N / ART. N / Articolo N / art. N → kind=article, depth=2\n"
        "- Art. N(M) / ART. N(M) → kind=subarticle, depth=3\n"
        "- Art. N paragraph M.M → kind=subarticle, depth=4\n"
        "- N.N / N.N.N decimal entries → kind=subarticle, depth=3 for N.N, depth=4 for N.N.N\n"
        "- ANNEX / ALLEGATO / ANNEX \"X\" → kind=annex, depth=1\n"
        "- Short ALL-CAPS lines or title-case headings with no numbering → kind=topic, depth=2\n\n"
        f"TOC TEXT:\n{toc_text}"
    )

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    entries_data = json.loads(raw)
    entries = []
    for item in entries_data:
        entries.append(
            HeadingEntry(
                title=item.get("title", ""),
                kind=item.get("kind", "topic"),
                depth=item.get("depth", 2),
                numbering=item.get("numbering"),
                page=item.get("page"),
                confidence=item.get("confidence"),
            )
        )
    return entries


def generate_summary(pre_toc_text: str, toc_text: str, client) -> str:
    """Generate a 2-3 sentence summary of the document using pre-TOC and TOC content."""
    prompt = (
        "You are summarizing a legal/academic document.\n\n"
        "Based on the document header and table of contents below, write a concise summary "
        "of 2-3 sentences describing:\n"
        "1. What this document is (type, issuing body)\n"
        "2. Its main purpose or subject\n"
        "3. The key topics it covers\n\n"
        "Write in plain English. Be specific. Do not invent details not present in the text.\n\n"
        f"DOCUMENT HEADER:\n{pre_toc_text[:2000]}\n\n"
        f"TABLE OF CONTENTS:\n{toc_text[:2000]}"
    )
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def extract_metadata(pre_toc_text: str, client) -> "DocumentMetadata":
    """Extract document metadata from the header section using Claude."""
    from scripts.models import DocumentMetadata

    prompt = (
        "Extract metadata from this document header. Return ONLY a JSON object with these keys:\n"
        '  "title": the full document title (string)\n'
        '  "year": academic year or date if present (string, e.g. "2025/26"), else null\n'
        '  "document_type": type of document (e.g. "Notice of competition", "Call for applications", "Bando di concorso"), else null\n'
        '  "organization": issuing organization/institution name, else null\n'
        '  "source": "explicit" if title is clearly stated as a heading, "inferred" if deduced from context\n\n'
        "Return ONLY the JSON object, no explanation.\n\n"
        f"DOCUMENT HEADER:\n{pre_toc_text[:2000]}"
    )
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    data = json.loads(raw)
    return DocumentMetadata(
        title=data.get("title", "Unknown"),
        source=data.get("source", "inferred"),
        year=data.get("year"),
        document_type=data.get("document_type"),
        organization=data.get("organization"),
    )


def extract_toc(file_path: str, client) -> "ExtractionResult":
    """Full pipeline: read file → detect TOC → classify → summarize → extract metadata."""
    import datetime
    from scripts.models import ExtractionResult, LogEntry

    log: list[LogEntry] = []

    lines = read_markdown_file(file_path)
    log.append(LogEntry(action="read", detail=f"Read {len(lines)} lines from {file_path}"))

    boundary = find_toc_boundaries(lines, client)
    if boundary is None:
        raise ValueError(f"No TOC section found in {file_path}")

    log.append(LogEntry(
        action="detected",
        detail=f"TOC marker '{boundary.marker}' at line {boundary.start_line}",
        line=boundary.start_line,
    ))
    log.append(LogEntry(
        action="boundary",
        detail=f"TOC spans lines {boundary.start_line}–{boundary.end_line}",
    ))

    toc_text = slice_toc_content(lines, boundary)
    pre_toc_text = extract_pre_toc_content(lines, boundary)

    print(f"INFO: TOC marker found at line {boundary.start_line}: '{boundary.marker}'", file=sys.stderr)
    print(f"INFO: TOC section spans lines {boundary.start_line}-{boundary.end_line}", file=sys.stderr)
    print(f"INFO: Sending {boundary.end_line - boundary.start_line + 1} TOC lines to LLM for classification", file=sys.stderr)

    flat_entries = classify_toc_entries(toc_text, client)
    log.append(LogEntry(action="classified", detail=f"LLM classified {len(flat_entries)} TOC entries"))

    kinds: dict[str, int] = {}
    for e in flat_entries:
        kinds[e.kind] = kinds.get(e.kind, 0) + 1
    kinds_str = ", ".join(f"{v} {k}s" for k, v in kinds.items())
    print(f"INFO: Classified {len(flat_entries)} entries ({kinds_str})", file=sys.stderr)

    heading_map = build_heading_map(flat_entries)
    log.append(LogEntry(action="mapped", detail=f"Built heading tree with {len(heading_map)} root nodes"))

    summary = generate_summary(pre_toc_text, toc_text, client)
    log.append(LogEntry(action="summarized", detail="Generated document summary"))

    metadata = extract_metadata(pre_toc_text, client)
    log.append(LogEntry(action="metadata", detail=f"Extracted metadata: title='{metadata.title}', source={metadata.source}"))

    return ExtractionResult(
        toc=flat_entries,
        heading_map=heading_map,
        summary=summary,
        metadata=metadata,
        toc_boundaries=boundary,
        processing_log=log,
        extracted_at=datetime.datetime.utcnow().isoformat() + "Z",
    )
