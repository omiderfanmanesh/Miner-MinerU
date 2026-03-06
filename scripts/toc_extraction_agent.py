"""CLI entry point for the TOC extraction agent.

Usage:
    python scripts/toc_extraction_agent.py <markdown_file_path> [--output <path>]

Exit codes:
    0 - success
    1 - file not found or unreadable
    2 - no TOC section detected
    3 - LLM API error

Provider is selected via LLM_PROVIDER in .env (or environment):
    LLM_PROVIDER=azure      → Azure OpenAI (gpt-4.1-mini by default)
    LLM_PROVIDER=anthropic  → Anthropic Claude (default)
"""
from __future__ import annotations

import argparse
import json
import sys

# Load .env if present (no error if missing)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed — fall back to plain env vars


def main():
    parser = argparse.ArgumentParser(
        description="Extract TOC and summary from a MinerU-generated markdown file."
    )
    parser.add_argument("markdown_file", help="Path to MinerU-generated markdown file")
    parser.add_argument("--output", "-o", help="Output JSON file path (default: stdout)", default=None)
    args = parser.parse_args()

    from scripts.llm_client import build_client
    client = build_client()

    print(f"INFO: Reading file: {args.markdown_file}", file=sys.stderr)

    try:
        from scripts.toc_extractor import extract_toc
        result = extract_toc(args.markdown_file, client)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        # Covers anthropic.APIError and other LLM failures
        print(f"ERROR: LLM API error: {e}", file=sys.stderr)
        sys.exit(3)

    output_json = json.dumps(result.to_dict(), indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"INFO: Output written to {args.output}", file=sys.stderr)
    else:
        print(output_json)

    print(f"INFO: Extraction complete.", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
