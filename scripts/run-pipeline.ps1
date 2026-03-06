#Requires -Version 5.0
<#
.SYNOPSIS
    Run the complete MinerU pipeline: extract TOC and fix markdown headings.

.DESCRIPTION
    Two-step pipeline:
    1. Extract TOC from markdown files (requires LLM API)
    2. Fix heading levels using extracted TOC (no API needed)

.PARAMETER DataDir
    Directory containing markdown files (default: ./data)

.PARAMETER OutputDir
    Directory for extracted TOC files (default: ./output)

.PARAMETER SkipExtraction
    Skip step 1, only run the fixer (default: $false)

.PARAMETER Provider
    LLM provider for extraction: 'anthropic' (default) or 'azure'

.EXAMPLE
    # Run complete pipeline
    .\run-pipeline.ps1

.EXAMPLE
    # Skip extraction, only fix (if TOC files exist)
    .\run-pipeline.ps1 -SkipExtraction

.EXAMPLE
    # Use Azure instead of Anthropic
    .\run-pipeline.ps1 -Provider azure

.NOTES
    For Anthropic: $env:ANTHROPIC_API_KEY = "sk-ant-..."
    For Azure: Set AZURE_OPENAI_* environment variables
#>

param(
    [string]$DataDir = "data",
    [string]$OutputDir = "output",
    [switch]$SkipExtraction,
    [ValidateSet('anthropic', 'azure')]
    [string]$Provider = 'anthropic'
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir

# Colors
$Colors = @{
    Success = "Green"
    Error   = "Red"
    Info    = "Cyan"
    Warning = "Yellow"
    Section = "Magenta"
}

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet('Success', 'Error', 'Info', 'Warning', 'Section')]
        [string]$Level = 'Info'
    )

    $timestamp = Get-Date -Format "HH:mm:ss"
    $color = $Colors[$Level]

    if ($Level -eq 'Section') {
        Write-Host ""
        Write-Host "=" * 80 -ForegroundColor $color
        Write-Host $Message -ForegroundColor $color
        Write-Host "=" * 80 -ForegroundColor $color
    }
    else {
        Write-Host "[$timestamp] " -NoNewline
        Write-Host $Message -ForegroundColor $color
    }
}

function Main {
    Push-Location $repoRoot

    try {
        Write-Log "MinerU Complete Pipeline" -Level Section

        # Step 1: Extract TOC
        if (-not $SkipExtraction) {
            Write-Log "Step 1: Extract TOC from Markdown Files" -Level Section

            # Find markdown files
            $mdFiles = @(Get-ChildItem -Path $DataDir -Filter "MinerU_markdown*.md" -Recurse -ErrorAction SilentlyContinue)

            if ($mdFiles.Count -eq 0) {
                Write-Log "No markdown files found in: $DataDir" -Level Error
                exit 1
            }

            Write-Log "Found $($mdFiles.Count) markdown file(s)" -Level Info
            Write-Host ""

            $extractedCount = 0
            $failedCount = 0

            foreach ($mdFile in $mdFiles) {
                Write-Host "Processing: " -NoNewline
                Write-Host $mdFile.Name -ForegroundColor Gray

                $mdName = [System.IO.Path]::GetFileNameWithoutExtension($mdFile.Name)
                $outputPath = "$OutputDir/$mdName.json"

                # Skip if already extracted
                if (Test-Path $outputPath) {
                    Write-Log "Already extracted (skipping)" -Level Info
                    $extractedCount++
                    Write-Host ""
                    continue
                }

                # Run extraction
                $pythonCmd = @(
                    "-m", "miner_mineru", "extract",
                    $mdFile.FullName,
                    "--output", $outputPath
                )

                $env:LLM_PROVIDER = $Provider

                $output = & python @pythonCmd 2>&1
                $exitCode = $LASTEXITCODE

                if ($exitCode -eq 0) {
                    Write-Log "Extracted" -Level Success
                    $extractedCount++
                }
                else {
                    Write-Log "Failed" -Level Error
                    $failedCount++
                }

                Write-Host ""
            }

            Write-Log "Extraction Summary: $extractedCount/$($mdFiles.Count) successful" -Level Info
            if ($failedCount -gt 0) {
                Write-Log "$failedCount file(s) failed" -Level Warning
            }
            Write-Host ""
        }

        # Step 2: Fix Markdown
        Write-Log "Step 2: Fix Heading Levels" -Level Section
        Write-Host ""

        # Run the fixer script
        $fixerScript = Join-Path $scriptDir "run-fixer.ps1"

        if (Test-Path $fixerScript) {
            & $fixerScript -DataDir $DataDir -OutputDir $OutputDir -FixedDir "output/fixed"
            $fixExitCode = $LASTEXITCODE
        }
        else {
            Write-Log "ERROR: Fixer script not found: $fixerScript" -Level Error
            exit 1
        }

        # Final summary
        Write-Host ""
        Write-Log "Pipeline Complete" -Level Section

        if ($fixExitCode -eq 0) {
            Write-Log "All steps completed successfully!" -Level Success
            Write-Host ""
            Write-Host "Next steps:" -ForegroundColor Cyan
            Write-Host "  1. Review corrected markdown files:"
            Write-Host "     Get-ChildItem output/fixed/*.md"
            Write-Host ""
            Write-Host "  2. Check correction reports:"
            Write-Host "     Get-ChildItem output/fixed/*_report.json"
            Write-Host ""
            exit 0
        }
        else {
            Write-Log "Pipeline completed with errors" -Level Warning
            exit 1
        }
    }
    finally {
        Pop-Location
    }
}

# Run pipeline
Main
