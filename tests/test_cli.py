"""CLI behavior tests."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from docstruct.interfaces import cli


def test_fix_command_passes_no_llm_flag_to_fix_markdown(capsys):
    with patch(
        "docstruct.interfaces.cli.fix_markdown",
        return_value=type(
            "Report",
            (),
            {
                "lines_changed": 1,
                "lines_demoted": 0,
                "unmatched_toc_entries": [],
                "to_dict": lambda self: {"ok": True},
            },
        )(),
    ) as mock_fix:
        with patch.object(
            sys,
            "argv",
            [
                "docstruct",
                "fix",
                "data/sample.md",
                "--toc",
                "output/01_toc/sample.json",
                "--output-dir",
                "output/02_fixed_markdown",
                "--report-dir",
                "output/02_fix_reports",
                "--no-llm",
            ],
        ):
            with pytest.raises(SystemExit) as excinfo:
                cli.main()

    assert excinfo.value.code == 0
    assert mock_fix.call_args.kwargs["use_llm_matching"] is False
    captured = capsys.readouterr()
    assert "Changed 1 headings" in captured.err


def test_normalize_command_passes_args_to_normalize_markdown(capsys):
    with patch(
        "docstruct.interfaces.cli.normalize_markdown",
        return_value=type(
            "Report",
            (),
            {
                "chunk_count": 3,
                "model": "gemma4",
                "to_dict": lambda self: {"ok": True},
            },
        )(),
    ) as mock_normalize:
        with patch.object(
            sys,
            "argv",
            [
                "docstruct",
                "normalize",
                "data/sample.md",
                "--output-dir",
                "output/02_normalized_markdown",
                "--report-dir",
                "output/02_normalize_reports",
                "--model",
                "gemma4",
                "--chunk-size",
                "5000",
                "--max-tokens",
                "1024",
                "--no-progress",
            ],
        ):
            with pytest.raises(SystemExit) as excinfo:
                cli.main()

    assert excinfo.value.code == 0
    assert mock_normalize.call_args.kwargs["model"] == "gemma4"
    assert mock_normalize.call_args.kwargs["chunk_size"] == 5000
    assert mock_normalize.call_args.kwargs["max_tokens"] == 1024
    assert mock_normalize.call_args.kwargs["show_progress"] is False
    captured = capsys.readouterr()
    assert "Chunks: 3" in captured.err
