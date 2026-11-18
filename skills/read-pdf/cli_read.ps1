#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Wrapper script for the read-pdf skill. Reads PDF files to markdown using
    the PdfHybridConverter from ai-system converter module.

.PARAMETER File
    Path to the PDF file.

.PARAMETER Page
    Optional page number to extract (1-based). If omitted, extracts full document.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$File,

    [Parameter()]
    [int]$Page
)

$ErrorActionPreference = "Stop"

$venvPython = "D:\Development\kb\ai-system\.venv\Scripts\python.exe"
$cliScript = Join-Path $PSScriptRoot "read_pdf.py"

$argList = @("--file", $File)
if ($Page) {
    $argList += @("--page", $Page)
}

& $venvPython $cliScript @argList
