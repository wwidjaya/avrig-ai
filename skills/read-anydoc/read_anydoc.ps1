#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Convert documents to Markdown using anydoc CLI with local OCR fallback.

.PARAMETER File
    Path to the document file.

.PARAMETER Output
    Optional output file path. If omitted, writes to stdout.

.PARAMETER Format
    Force input format (for CSV from stdin or wrong extension).

.PARAMETER Dpi
    PDF render DPI for OCR fallback (default: 200).

.PARAMETER OcrModel
    OCR model ID (default: ocr).

.PARAMETER OcrBaseUrl
    Local OCR API base URL (default: http://localhost:20128/v1).

.PARAMETER KeepImages
    Keep extracted page images after OCR (default: false).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$File,

    [Alias("o")]
    [string]$Output,
    [string]$Format,
    [int]$Dpi = 200,
    [string]$OcrModel = "ocr",
    [string]$OcrBaseUrl = "http://localhost:20128/v1",
    [switch]$KeepImages
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$argList = @("-y", "@firecrawl/anydoc", $File)
if ($Output) { $argList += @("-o", $Output) }
if ($Format) { $argList += @("--format", $Format) }

$exitCode = 0
try {
    & npx @argList
    $exitCode = $LASTEXITCODE
} catch {
    $exitCode = 1
}

if ($exitCode -ne 3) { exit $exitCode }

Write-Host "anydoc: scanned PDF detected, falling back to local OCR..." -ForegroundColor Yellow

$venvPython = "D:\miniconda3\envs\kb\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = (Get-Command python3 -ErrorAction SilentlyContinue).Source
    if (-not $python) { $python = (Get-Command python -ErrorAction SilentlyContinue).Source }
}
if (-not $python) {
    Write-Error "Python not found. Install or activate kb conda env for OCR fallback."
    exit 1
}

$ocrScript = Join-Path $scriptDir "ocr_pdf.py"
$ocrArgs = @($ocrScript, "--file", $File, "--base-url", $OcrBaseUrl, "--dpi", $Dpi, "--ocr-model", $OcrModel)
if ($Output) { $ocrArgs += @("--output", $Output) }
if ($KeepImages) { $ocrArgs += "--keep-images" }

& $python @ocrArgs
exit $LASTEXITCODE
