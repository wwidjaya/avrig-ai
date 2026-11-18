#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Read image via OCR API. Extracts text from an image using the local
    ocr model at http://localhost:20128/v1.

.PARAMETER File
    Path to the image file.

.PARAMETER Prompt
    Optional instruction prompt for the OCR model.

.PARAMETER Output
    Optional file path to write extracted text. If omitted, writes to stdout.

.PARAMETER BaseUrl
    API base URL (default: http://localhost:20128/v1).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$File,

    [string]$Prompt = "Extract all text from this image. Preserve structure and layout.",

    [string]$Output,

    [string]$BaseUrl = "http://localhost:20128/v1"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "read_image.py"

$venvPython = "D:\miniconda3\envs\kb\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = (Get-Command python3 -ErrorAction SilentlyContinue).Source
    if (-not $python) {
        $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    }
}
if (-not $python) {
    Write-Error "Python interpreter not found. Install python or activate the kb conda env."
}

$argList = @($pythonScript, "--file", $File, "--base-url", $BaseUrl)
if ($Prompt) {
    $argList += @("--prompt", $Prompt)
}
if ($Output) {
    $argList += @("--output", $Output)
}

& $python @argList
