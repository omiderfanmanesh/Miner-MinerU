#!/usr/bin/env python
"""Normalize a markdown file with a local Ollama model."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from docstruct.output_layout import NORMALIZED_MARKDOWN_DIR, NORMALIZE_REPORTS_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize a markdown file with chunked Ollama calls")
    parser.add_argument("markdown_file", help="Path to markdown file")
    parser.add_argument(
        "--output-dir",
        "-o",
        default=str(NORMALIZED_MARKDOWN_DIR),
        help="Directory where normalized markdown will be written",
    )
    parser.add_argument(
        "--report-dir",
        default=str(NORMALIZE_REPORTS_DIR),
        help="Directory where normalization reports will be written",
    )
    parser.add_argument("--model", default=None, help="Ollama model name, for example gemma4")
    parser.add_argument("--base-url", default=None, help="Ollama base URL")
    parser.add_argument("--chunk-size", type=int, default=6000, help="Approximate maximum input characters per chunk")
    parser.add_argument("--max-tokens", type=int, default=2048, help="Maximum tokens per chunk response")
    parser.add_argument("--no-progress", action="store_true", help="Disable chunk progress output")
    args = parser.parse_args()

    markdown_file = Path(args.markdown_file)
    if not markdown_file.is_absolute():
        markdown_file = (PROJECT_ROOT / markdown_file).resolve()

    if not markdown_file.exists():
        print(f"ERROR: File not found: {markdown_file}")
        raise SystemExit(1)

    output_dir = (PROJECT_ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir = (PROJECT_ROOT / args.report_dir).resolve()
    report_dir.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    cmd = [
        sys.executable,
        "-m",
        "docstruct",
        "normalize",
        str(markdown_file),
        "--output-dir",
        str(output_dir),
        "--report-dir",
        str(report_dir),
        "--chunk-size",
        str(args.chunk_size),
        "--max-tokens",
        str(args.max_tokens),
    ]
    if args.model:
        cmd.extend(["--model", args.model])
    if args.base_url:
        cmd.extend(["--base-url", args.base_url])
    if args.no_progress:
        cmd.append("--no-progress")

    print(f"Normalizing: {markdown_file}")
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    print(f"Saved normalized outputs to: {output_dir}")


if __name__ == "__main__":
    main()
