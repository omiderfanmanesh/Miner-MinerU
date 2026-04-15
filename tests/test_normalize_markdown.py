"""Tests for chunked Ollama markdown normalization."""

from __future__ import annotations

import json
import os
import tempfile

from docstruct.application.normalize_markdown import normalize_markdown, split_markdown_into_chunks


class _FakeClient:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def create_message(self, *, model: str, max_tokens: int, messages: list[dict]) -> str:
        self.calls.append(
            {
                "model": model,
                "max_tokens": max_tokens,
                "messages": messages,
            }
        )
        return self._responses.pop(0)


def test_split_markdown_into_chunks_breaks_at_article_boundary():
    markdown = "\n".join(
        [
            "# Notice",
            "",
            "Opening paragraph that is intentionally long enough to push the chunk over the configured limit.",
            "",
            "Art. 1 - Definitions",
            "Body for the first article.",
            "",
            "Art. 2 - Requirements",
            "Body for the second article.",
        ]
    )

    chunks = split_markdown_into_chunks(markdown, chunk_size=70)

    assert len(chunks) == 2
    assert chunks[0].text.endswith("configured limit.")
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 3
    assert "Art. 1 - Definitions" in chunks[1].text
    assert chunks[1].start_line == 4


def test_normalize_markdown_writes_chunked_output_and_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = os.path.join(tmpdir, "source.md")
        with open(source_path, "w", encoding="utf-8") as handle:
            handle.write(
                "# Notice\n\n"
                "Art. 1 - Definitions noisy 11\n"
                "Messy paragraph.\n\n"
                "Art. 2 - Requirements\n"
                "Another paragraph.\n"
            )

        fake_client = _FakeClient(
            [
                "```markdown\n## Art. 1 - Definitions\nMessy paragraph.\n```",
                "## Art. 2 - Requirements\nAnother paragraph.",
            ]
        )

        output_dir = os.path.join(tmpdir, "normalized")
        report_dir = os.path.join(tmpdir, "reports")
        report = normalize_markdown(
            source_path,
            output_dir,
            report_dir=report_dir,
            model="gemma4",
            chunk_size=40,
            max_tokens=512,
            show_progress=False,
            client=fake_client,
        )

        output_path = os.path.join(output_dir, "source.md")
        with open(output_path, "r", encoding="utf-8") as handle:
            normalized = handle.read()

        assert "## Art. 1 - Definitions" in normalized
        assert "## Art. 2 - Requirements" in normalized
        assert report.model == "gemma4"
        assert report.chunk_count == 2

        report_path = os.path.join(report_dir, "source_normalize_report.json")
        with open(report_path, "r", encoding="utf-8") as handle:
            report_json = json.load(handle)

        assert report_json["chunk_count"] == 2
        assert report_json["chunks"][0]["start_line"] == 1
        assert report_json["chunks"][1]["start_line"] == 5
        assert fake_client.calls[1]["model"] == "gemma4"
        assert "## Art. 1 - Definitions" in fake_client.calls[1]["messages"][1]["content"]
