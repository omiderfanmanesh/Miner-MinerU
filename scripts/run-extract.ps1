#Requires -Version 5.0
<#
.SYNOPSIS
    Extract TOC from markdown files using the MinerU extraction pipeline.

.DESCRIPTION
    Extracts table of contents from markdown files and saves as JSON.
    Requires Anthropic or Azure OpenAI API credentials.

.PARAMETER MarkdownFile
    Path to markdown file to process (required).

.PARAMETER OutputFile
    Output JSON file path (default: output/<filename>.json)

.PARAMETER Provider
    LLM provider: 'anthropic' (default) or 'azure'

.EXAMPLE
    .\run-extract.ps1 -MarkdownFile "data\notice.md"

.EXAMPLE
    .\run-extract.ps1 -MarkdownFile "data\notice.md" -OutputFile "output\notice_toc.json" -Provider anthropic

.NOTES
    Set environment variables before running:
    - Anthropic: $env:ANTHROPIC_API_KEY = "sk-ant-..."
    - Azure: Set AZURE_OPENAI_* variables
#>

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$MarkdownFile,

    [string]$OutputFile,

    [ValidateSet('anthropic', 'azure')]
    [string]$Provider = 'anthropic'
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

function Main {
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor Cyan
    Write-Host "MinerU TOC Extraction" -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Cyan
    Write-Host ""

    # Validate markdown file
    if (-not (Test-Path $MarkdownFile)) {
        Write-Log "ERROR: Markdown file not found: $MarkdownFile" -Level Error
        exit 1
    }

    Write-Log "Input: $(Resolve-Path $MarkdownFile)" -Level Info

    # Determine output file
    if (-not $OutputFile) {
        $mdName = [System.IO.Path]::GetFileNameWithoutExtension($MarkdownFile)
        $OutputFile = "output/$mdName.json"
    }

    Write-Log "Output: $OutputFile" -Level Info

    # Create output directory
    $outputDir = Split-Path $OutputFile
    if ($outputDir -and -not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        Write-Log "Created output directory: $outputDir" -Level Info
    }

    # Set LLM provider
    Write-Log "Provider: $Provider" -Level Info
    $env:LLM_PROVIDER = $Provider

    # Validate API key
    if ($Provider -eq 'anthropic') {
        if (-not $env:ANTHROPIC_API_KEY) {
            Write-Log "ERROR: ANTHROPIC_API_KEY environment variable not set" -Level Error
            Write-Log "Set it with: `$env:ANTHROPIC_API_KEY = 'sk-ant-...'" -Level Info
            exit 1
        }
        Write-Log "Using Anthropic API" -Level Success
    }
    elseif ($Provider -eq 'azure') {
        @('AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_DEPLOYMENT') |
        ForEach-Object {
            if (-not (Get-Item -Path "env:$_" -ErrorAction SilentlyContinue)) {
                Write-Log "ERROR: $_ environment variable not set" -Level Error
                exit 1
            }
        }
        Write-Log "Using Azure OpenAI API" -Level Success
    }

    Write-Host ""
    Write-Log "Starting extraction..." -Level Info
    Write-Host ""

    # Run extraction
    $pythonCmd = @(
        "-m", "miner_mineru", "extract",
        $MarkdownFile,
        "--output", $OutputFile
    )

    try {
        $output = & python @pythonCmd 2>&1
        $exitCode = $LASTEXITCODE

        if ($exitCode -eq 0) {
            Write-Host ""
            Write-Log "Extraction completed successfully!" -Level Success
            Write-Log "Output: $(Resolve-Path $OutputFile)" -Level Info

            # Show file size
            if (Test-Path $OutputFile) {
                $fileSize = (Get-Item $OutputFile).Length
                $fileSizeKB = [math]::Round($fileSize / 1KB, 2)
                Write-Log "File size: $fileSizeKB KB" -Level Info
            }

            exit 0
        }
        else {
            Write-Host ""
            Write-Log "Extraction failed with exit code: $exitCode" -Level Error

            # Show error output
            if ($output) {
                Write-Host ""
                Write-Host "Error details:" -ForegroundColor Red
                foreach ($line in $output) {
                    if ($line -match 'ERROR|error') {
                        Write-Host "  $line" -ForegroundColor Red
                    }
                }
            }

            exit 1
        }
    }
    catch {
        Write-Log "Error running extraction: $_" -Level Error
        exit 1
    }
}

# Run main function
Main
