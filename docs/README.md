# Documentation

Complete documentation for the Miner-MinerU pipeline implementation.

## Quick Navigation

### Getting Started
- **[Quick Start](./guides/QUICK_START.md)** - One-liner commands and basic usage (START HERE)
- **[Batch Pipeline Guide](./guides/BATCH_PIPELINE.md)** - Comprehensive guide with all options and examples

### Architecture & Technical Details
- **[Pipeline Summary](./architecture/PIPELINE_SUMMARY.md)** - Complete overview with test results and performance metrics
- **[LLM Agent Implementation](./architecture/LLM_AGENT_IMPLEMENTATION.md)** - Technical details of the LLM-based heading correction

## Structure

```
docs/
├── README.md                    (this file)
├── guides/                      (user-facing documentation)
│   ├── QUICK_START.md          (fast commands to get started)
│   └── BATCH_PIPELINE.md       (complete guide with examples)
└── architecture/               (technical documentation)
    ├── PIPELINE_SUMMARY.md     (implementation overview)
    └── LLM_AGENT_IMPLEMENTATION.md (technical details)
```

## What Each Document Covers

### guides/QUICK_START.md
- One-line commands for common tasks
- Basic usage patterns
- Simple troubleshooting
- Key features overview

### guides/BATCH_PIPELINE.md
- Complete command reference
- Environment setup instructions
- Workflow examples (4 detailed examples)
- Output structure and schemas
- Performance notes
- Advanced customization options
- Comprehensive troubleshooting

### architecture/PIPELINE_SUMMARY.md
- High-level overview of the complete system
- Test results (16/16 tests passing)
- Architecture diagram
- Code quality metrics
- Known limitations and future improvements
- File structure and organization

### architecture/LLM_AGENT_IMPLEMENTATION.md
- Detailed technical implementation
- How the LLM agent works
- API integration details
- Advantages over previous regex approach
- Backward compatibility notes

## Quick Start Command

```bash
# Fast processing (no API calls)
python scripts/run_pipeline_all.py --skip-extract --no-llm
```

## Key Components

1. **TOC Extraction Agent** - Analyzes document structure with Claude LLM
2. **Markdown Fixer** - Normalizes heading levels using extracted TOC
3. **LLM Heading Corrector** - Intelligently determines heading levels for unmatched content
4. **Batch Pipeline Runner** - Processes all documents with a single command

## Test Status

✅ All 16 unit tests passing
✅ Batch processing verified with real documents
✅ 113 total lines corrected across 2 tested documents

## Implementation Status

✅ LLM agent created and integrated
✅ Markdown fixer updated with LLM support
✅ Batch pipeline runner implemented
✅ Complete test suite passing
✅ Documentation complete

For more details, start with [Quick Start](./guides/QUICK_START.md).
