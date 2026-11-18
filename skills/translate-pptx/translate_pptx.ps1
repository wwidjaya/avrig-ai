#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Translate a .pptx file from Indonesian to English.

.DESCRIPTION
    Phase 1 (Extract):  Extracts text segments from a .pptx into a JSON file.
    Phase 2 (Apply):    Applies translations from JSON back into the .pptx.

.PARAMETER Extract
    Run extract phase.

.PARAMETER Apply
    Run apply phase.

.PARAMETER Path
    Path to the .pptx file.

.EXAMPLE
    pwsh translate_pptx.ps1 -Extract -Path "D:\docs\presentasi.pptx"
    pwsh translate_pptx.ps1 -Apply -Path "D:\docs\presentasi.pptx"
#>

param(
    [switch]$Extract,
    [switch]$Apply,
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$scriptDir = $PSScriptRoot
$pyScript = Join-Path $scriptDir "translate_pptx.py"

if (-not (Test-Path -LiteralPath $Path)) {
    Write-Error "File not found: $Path"
    exit 1
}

if ($Extract) {
    $jsonPath = "$Path.segments.json"
    python "$pyScript" extract "$Path" "$jsonPath"
    exit $LASTEXITCODE
}

if ($Apply) {
    $jsonPath = "$Path.segments.json"
    if (-not (Test-Path -LiteralPath $jsonPath)) {
        Write-Error "Translations file not found: $jsonPath`nRun extract phase first."
        exit 1
    }
    python "$pyScript" apply "$Path" "$jsonPath"
    exit $LASTEXITCODE
}

Write-Error "Specify -Extract or -Apply."
exit 1
