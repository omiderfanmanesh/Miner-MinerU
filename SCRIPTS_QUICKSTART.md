# Scripts Quick Start Guide

Bash scripts for the MinerU pipeline - perfect for use with Anaconda!

## One-Minute Setup

```bash
# 1. Navigate to repo
cd /c/Projects/personal/Miner-MinerU

# 2. Activate conda environment
conda activate agent

# 3. Set API key (only if extracting TOC)
export ANTHROPIC_API_KEY="sk-ant-..."

# 4. Run the fixer (NO LLM NEEDED - uses pre-extracted TOC)
bash scripts/run-fixer.sh
```

Done! Your markdown files will be corrected in `output/fixed/`

## Script Overview

| Script | Purpose | LLM Required? | Time |
|--------|---------|---------------|------|
| `run-fixer.sh` | Fix markdown headings | ❌ No | 1 min |
| `run-extract.sh` | Extract TOC from markdown | ✅ Yes | 10 sec/file |
| `run-pipeline.sh` | Extract + Fix (complete) | ✅ Yes | 2-5 min |

## Usage Examples

### Option 1: Fix Only (Easiest)

Pre-extracted TOC files already exist in `output/`

```bash
bash scripts/run-fixer.sh
```

**Output:**
- Corrected markdown: `output/fixed/*.md`
- Reports: `output/fixed/*_report.json`

### Option 2: Extract Single File

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
bash scripts/run-extract.sh data/notice.md
```

### Option 3: Complete Pipeline

Extract all files, then fix all files:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
bash scripts/run-pipeline.sh
```

## Available Options

### `run-fixer.sh`
```bash
bash scripts/run-fixer.sh [options]

Options:
  --data-dir <path>      Source markdown directory (default: data)
  --output-dir <path>    TOC files directory (default: output)
  --fixed-dir <path>     Output directory (default: output/fixed)
  --verbose              Show detailed output
```

### `run-extract.sh`
```bash
bash scripts/run-extract.sh <markdown_file> [options]

Options:
  -o, --output <file>    Output JSON path (default: output/<filename>.json)
  -p, --provider         anthropic or azure (default: anthropic)
```

### `run-pipeline.sh`
```bash
bash scripts/run-pipeline.sh [options]

Options:
  --data-dir <path>      Source markdown directory
  --output-dir <path>    TOC files directory
  --provider <provider>  anthropic or azure
  --skip-extraction      Only run fixer (skip extraction)
```

## API Setup (Required for Extraction)

### Anthropic (Recommended)

```bash
# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Verify it's set
echo $ANTHROPIC_API_KEY
```

### Azure OpenAI

```bash
export LLM_PROVIDER="azure"
export AZURE_OPENAI_API_KEY="your-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="gpt-4"
export AZURE_OPENAI_API_VERSION="2024-02-15-preview"
```

## Real-World Workflow

```bash
# 1. Setup environment once
conda activate agent
export ANTHROPIC_API_KEY="sk-ant-..."

# 2. Run fixer on pre-extracted files
bash scripts/run-fixer.sh

# 3. Check results
ls -lh output/fixed/*.md
cat output/fixed/notice_report.json | jq .lines_changed
```

## Output Format

Each corrected file includes:

**Markdown file** (`output/fixed/notice.md`):
```markdown
# SECTION I

## ART. 1 - Definitions

Article text here...

### ART. 1(1) - Special Case

More text...
```

**Report file** (`output/fixed/notice_report.json`):
```json
{
  "source_file": "data/notice.md",
  "total_lines": 5022,
  "lines_changed": 252,
  "lines_demoted": 1,
  "unmatched_toc_entries": [
    "Complex Topic",
    "Another Topic"
  ],
  "corrections": [...]
}
```

## Color Output

Scripts use colors for easy reading:
- 🟦 **Cyan**: General info
- 🟩 **Green**: Success messages
- 🟥 **Red**: Errors
- 🟨 **Yellow**: Warnings

## Troubleshooting

### "No TOC files found"

Extract TOC first:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
bash scripts/run-extract.sh data/notice.md
```

### "No markdown files found"

Make sure markdown files are in the `data/` directory:
```bash
ls data/MinerU_markdown*.md
```

### "ANTHROPIC_API_KEY not set"

Only needed for extraction:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Path Issues

Always run scripts from repo root:
```bash
cd /c/Projects/personal/Miner-MinerU
bash scripts/run-fixer.sh
```

## Next Steps

1. **Fix your documents**:
   ```bash
   bash scripts/run-fixer.sh
   ```

2. **Review corrected files**:
   ```bash
   ls -lh output/fixed/
   ```

3. **Check reports for details**:
   ```bash
   cat output/fixed/notice_report.json
   ```

## Tips

- Use `--skip-extraction` if you've already extracted TOC files
- Combine with `jq` for powerful JSON processing:
  ```bash
  cat output/fixed/*_report.json | jq '.lines_changed'
  ```
- Run multiple times safely - script skips already-extracted files

## Documentation

For detailed information, see:
- [scripts/README.md](scripts/README.md) - Complete script documentation
- [PIPELINE_GUIDE.md](PIPELINE_GUIDE.md) - Full pipeline guide
- [CLAUDE.md](CLAUDE.md) - Project structure

---

**Happy processing!** 🚀
