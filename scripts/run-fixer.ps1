#Requires -Version 5.0
<#
.SYNOPSIS
    Run the MinerU markdown fixer on all markdown/TOC file pairs.

.DESCRIPTION
    This script processes all markdown files with matching extracted TOC files.
    It normalizes heading levels and generates corrected markdown + reports.

    No LLM setup required - uses pre-extracted TOC files.

.PARAMETER DataDir
    Directory containing markdown files (default: ./data)

.PARAMETER OutputDir
    Directory containing extracted TOC JSON files (default: ./output)

.PARAMETER FixedDir
    Output directory for corrected files (default: ./output/fixed)

.EXAMPLE
    .\run-fixer.ps1

.EXAMPLE
    .\run-fixer.ps1 -DataDir "C:\data" -OutputDir "C:\output"

.NOTES
    Requires Python 3.9+ with miner_mineru package installed.
    Set conda environment: conda activate agent
#>

param(
    [string]$DataDir = "data",
    [string]$OutputDir = "output",
    [string]$FixedDir = "output/fixed",
    [switch]$Verbose
)

# Colors for output
$Colors = @{
    Success = "Green"
    Error   = "Red"
    Info    = "Cyan"
    Warning = "Yellow"
}

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet('Success', 'Error', 'Info', 'Warning')]
        [string]$Level = 'Info'
    )

    $timestamp = Get-Date -Format "HH:mm:ss"
    $color = $Colors[$Level]
    Write-Host "[$timestamp] " -NoNewline
    Write-Host $Message -ForegroundColor $color
}

function Get-MarkdownFiles {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        Write-Log "ERROR: Data directory not found: $Path" -Level Error
        exit 1
    }

    $files = Get-ChildItem -Path $Path -Filter "MinerU_markdown*.md" -Recurse |
             Sort-Object FullName

    return $files
}

function Get-TOCFiles {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return @()
    }

    $files = Get-ChildItem -Path $Path -Filter "*.json" -File |
             Where-Object { -not $_.Name.EndsWith('_report.json') } |
             Sort-Object Name

    return $files
}

function Find-MatchingTOC {
    param(
        [string]$MarkdownFile,
        [object[]]$TOCFiles
    )

    $mdName = [System.IO.Path]::GetFileNameWithoutExtension($MarkdownFile)

    # Exact match first
    $exact = $TOCFiles | Where-Object {
        [System.IO.Path]::GetFileNameWithoutExtension($_.Name) -eq $mdName
    }

    if ($exact) {
        return $exact[0].FullName
    }

    # Partial match
    $partial = $TOCFiles | Where-Object {
        $mdName.StartsWith([System.IO.Path]::GetFileNameWithoutExtension($_.Name))
    }

    if ($partial) {
        return $partial[0].FullName
    }

    return $null
}

function Run-Fixer {
    param(
        [string]$MarkdownFile,
        [string]$TOCFile,
        [string]$OutputDir
    )

    $mdName = Split-Path $MarkdownFile -Leaf
    $tocName = Split-Path $TOCFile -Leaf

    Write-Log "Processing: $mdName" -Level Info
    Write-Log "Using TOC: $tocName" -Level Info

    # Create output directory
    if (-not (Test-Path $OutputDir)) {
        New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    }

    # Run fixer command
    $pythonCmd = @(
        "-m", "miner_mineru", "fix",
        $MarkdownFile,
        "--toc", $TOCFile,
        "--output-dir", $OutputDir
    )

    try {
        $output = & python @pythonCmd 2>&1

        # Check for success
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Success!" -Level Success

            # Parse and display results from report file
            $mdBaseName = [System.IO.Path]::GetFileNameWithoutExtension($MarkdownFile)
            $reportPath = Join-Path $OutputDir "$mdBaseName`_report.json"

            if (Test-Path $reportPath) {
                try {
                    $report = Get-Content $reportPath | ConvertFrom-Json

                    Write-Host "  Results:" -ForegroundColor Gray
                    Write-Host "    Total lines:         $($report.total_lines)" -ForegroundColor Gray
                    Write-Host "    Lines changed:       $($report.lines_changed)" -ForegroundColor Gray
                    Write-Host "    Lines demoted:       $($report.lines_demoted)" -ForegroundColor Gray
                    Write-Host "    Unmatched TOC items: $(($report.unmatched_toc_entries | Measure-Object).Count)" -ForegroundColor Gray
                    Write-Host ""
                }
                catch {
                    if ($Verbose) {
                        Write-Log "Could not parse report: $_" -Level Warning
                    }
                }
            }

            return $true
        }
        else {
            Write-Log "Failed with exit code: $LASTEXITCODE" -Level Error
            if ($Verbose) {
                Write-Host $output
            }
            return $false
        }
    }
    catch {
        Write-Log "Error running fixer: $_" -Level Error
        return $false
    }
}

function Main {
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor Cyan
    Write-Host "MinerU Markdown Fixer - Normalize Heading Levels" -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Cyan
    Write-Host ""

    # Find markdown files
    Write-Log "Scanning for markdown files in: $DataDir" -Level Info
    $mdFiles = @(Get-MarkdownFiles $DataDir)

    if ($mdFiles.Count -eq 0) {
        Write-Log "No MinerU markdown files found in: $DataDir" -Level Warning
        exit 1
    }

    Write-Log "Found $($mdFiles.Count) markdown file(s)" -Level Info

    # Find TOC files
    Write-Log "Scanning for TOC files in: $OutputDir" -Level Info
    $tocFiles = @(Get-TOCFiles $OutputDir)

    if ($tocFiles.Count -eq 0) {
        Write-Log "No TOC JSON files found in: $OutputDir" -Level Error
        Write-Log "Please extract TOC files first using:" -Level Info
        Write-Log "  python -m miner_mineru extract <markdown_file> --output output/<name>.json" -Level Info
        exit 1
    }

    Write-Log "Found $($tocFiles.Count) TOC file(s)" -Level Info
    Write-Host ""

    # Match files
    $pairs = @()
    $skipped = @()

    foreach ($mdFile in $mdFiles) {
        $matchingTOC = Find-MatchingTOC $mdFile.FullName $tocFiles

        if ($matchingTOC) {
            $pairs += @{
                Markdown = $mdFile.FullName
                TOC      = $matchingTOC
            }
        }
        else {
            $skipped += $mdFile.Name
        }
    }

    if ($skipped.Count -gt 0) {
        Write-Log "Skipping $($skipped.Count) file(s) without matching TOC:" -Level Warning
        foreach ($file in $skipped) {
            Write-Host "  - $file" -ForegroundColor Yellow
        }
        Write-Host ""
    }

    if ($pairs.Count -eq 0) {
        Write-Log "No markdown/TOC pairs found to process" -Level Error
        exit 1
    }

    Write-Log "Processing $($pairs.Count) file pair(s):" -Level Info
    Write-Host ""

    # Process each pair
    $successful = 0
    $failed = 0

    foreach ($i in 1..$pairs.Count) {
        $pair = $pairs[$i - 1]

        Write-Host ("=" * 80) -ForegroundColor Gray
        Write-Host "[$i/$($pairs.Count)]" -ForegroundColor Gray -NoNewline
        Write-Host " "

        if (Run-Fixer $pair.Markdown $pair.TOC $FixedDir) {
            $successful++
        }
        else {
            $failed++
        }
    }

    # Summary
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor Cyan
    Write-Host "Pipeline Complete" -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Cyan

    $status = if ($failed -eq 0) { "Success" } else { "Partial" }
    $statusColor = if ($failed -eq 0) { "Green" } else { "Yellow" }

    Write-Host "Status:      " -NoNewline
    Write-Host $status -ForegroundColor $statusColor
    Write-Host "Successful:  $successful/$($pairs.Count)"
    Write-Host "Failed:      $failed/$($pairs.Count)"
    Write-Host ""
    Write-Host "Output:      $(Resolve-Path $FixedDir)" -ForegroundColor Cyan
    Write-Host "Reports:     $FixedDir/*_report.json" -ForegroundColor Cyan
    Write-Host ""

    exit if ($failed -gt 0) { 1 } else { 0 }
}

# Run main function
Main
