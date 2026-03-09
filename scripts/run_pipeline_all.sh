#!/bin/bash
# Batch pipeline runner: Extract TOC and fix markdown for all documents

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="/c/Users/ERO8OFO/.conda/envs/agent/python.exe"

# Run pipeline
PYTHONNOUSERSITE=1 "$PYTHON" "$PROJECT_ROOT/scripts/run_pipeline_all.py" "$@"
