#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Translate a .docx file between languages, preserving run-level formatting.

.DESCRIPTION
    One-shot translation via an Ollama LLM. Preserves bold/italic/underline,
    fonts, sizes, colors, tables, TOC areas, headers/footers, footnotes,
    endnotes, comments, and textboxes. The original file is never modified;
    a new .{TargetLang}.docx is written next to it (or to -Output).

.PARAMETER Path
    Path to the .docx file.

.PARAMETER SourceLang
    Source language name (default: Indonesian).

.PARAMETER TargetLangName
    Target language name for the LLM (default: English).

.PARAMETER TargetLang
    Target language code used for the output suffix (default: en).

.PARAMETER OllamaModel
    Ollama model name (default: gemma4:latest).

.PARAMETER OllamaHost
    Ollama host (default: 10.30.200.32).

.PARAMETER OllamaPort
    Ollama port (default: 11434).

.PARAMETER Output
    Optional explicit output .docx path. Defaults to
    <docFolder>\<BaseName>.<TargetLang>.docx.

.PARAMETER Config
    Optional JSON config file (keys mirror TranslatorConfig fields:
    glossary/fixed_terms, word_repairs, toc_headings, temperature, ...).

.PARAMETER DryRun
    Scan the document and report what would be translated, without calling
    the LLM.

.PARAMETER ShowProgress
    Print per-paragraph progress.

.EXAMPLE
    pwsh translate_docx.ps1 -Path "D:\docs\laporan.docx"
    pwsh translate_docx.ps1 -Path "D:\docs\document.docx" -SourceLang "French" -TargetLangName "Chinese" -TargetLang "zh"
    pwsh translate_docx.ps1 -Path "D:\docs\laporan.docx" -DryRun -ShowProgress
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$Path,
    [string]$SourceLang = "Indonesian",
    [string]$TargetLangName = "English",
    [string]$TargetLang = "en",
    [string]$OllamaModel = "gemma4:latest",
    [string]$OllamaHost = "10.30.200.32",
    [string]$OllamaPort = "11434",
    [string]$Output,
    [string]$Config,
    [switch]$DryRun,
    [switch]$ShowProgress
)

$scriptDir = $null
if ($PSCommandPath) { $scriptDir = Split-Path -Path $PSCommandPath -Parent }
if (-not $scriptDir -and $MyInvocation.MyCommand.Path) { $scriptDir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent }
if (-not $scriptDir) { throw "Cannot determine script directory. Run the script directly (not via dot-sourcing or invocation from another script)." }
$pyScript = Join-Path -Path $scriptDir -ChildPath "translate_docx.py"

if (-not (Test-Path -LiteralPath $Path)) {
    Write-Error "File not found: $Path"
    exit 1
}

if (-not $Output) {
    $docItem = Get-Item -LiteralPath $Path
    $Output = Join-Path -Path $docItem.DirectoryName -ChildPath "$($docItem.BaseName).$TargetLang.docx"
}

$pyArgs = @(
    $Path,
    '-o', $Output,
    '--source', $SourceLang,
    '--target', $TargetLangName,
    '--model', $OllamaModel,
    '--host', $OllamaHost,
    '--port', $OllamaPort
)
if ($Config) { $pyArgs += '--config', $Config }
if ($DryRun) { $pyArgs += '--dry-run' }
if ($ShowProgress) { $pyArgs += '-v' }

# Resolve a Python interpreter that has python-docx and requests installed.
# The profile may shadow `python` with an env lacking these modules, so a
# few well-known alternatives are also probed.
$candidates = @()
foreach ($name in @('python', 'python3')) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) { $candidates += $cmd.Source }
}
$curPython = (Get-Command python -ErrorAction SilentlyContinue).Source
if ($curPython -match '^(.+)\\envs\\[^\\]+\\python\.exe$') {
    $candidates += "$($Matches[1])\python.exe"
}
$pyCmd = Get-Command py -ErrorAction SilentlyContinue
if ($pyCmd -and $pyCmd.Source) { $candidates += $pyCmd.Source }
if (Test-Path -LiteralPath 'C:\Windows\py.exe') { $candidates += 'C:\Windows\py.exe' }
$candidates += where.exe python 2>$null

$pythonExe = $null
$pythonPrefix = @()
foreach ($exe in ($candidates | Where-Object { $_ } | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $exe)) { continue }
    & $exe -c "import docx, requests" 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $pythonExe = $exe
        if ((Split-Path -Leaf $exe) -eq 'py.exe') { $pythonPrefix = @('-3') }
        break
    }
}
if (-not $pythonExe) {
    Write-Error "No Python interpreter with 'docx' and 'requests' found. Install them with: pip install python-docx requests"
    exit 1
}

& $pythonExe @pythonPrefix "$pyScript" @pyArgs
exit $LASTEXITCODE
