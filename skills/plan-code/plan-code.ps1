#Requires -Version 7.0
<#
  plan-code.ps1

  Plan code allocation ledger for avrig-ai projects.

  Two files carry the record:
    plans/_plan.sql   deterministic SQL dump, committed to git, the durable record
    plans/_plan.db    working SQLite database, local only, rebuilt by import

  plans/PLAN-RULES.md is hand written and declares the project indicator in its
  frontmatter. This tool reads that declaration and never writes the file.

  The cycle is import (load the dump), assign (add one row), export (rewrite the
  dump), verify (prove the dump, the database, and the git union agree).

  Exit codes: 0 ok, 1 verification or drift failure, 2 contention after the busy
  timeout, 3 invalid input or configuration, 4 git failure (an attempted fetch
  that did not complete included).

  Untrusted text never reaches SQL as interpolation: titles, branches, plan paths
  and reasons travel as a one element JSON array in a BOM free temp file, read
  with json_each(readfile(:payload)) and lifted with json_extract().
#>

$ErrorActionPreference = 'Stop'
$OutputEncoding = [Text.UTF8Encoding]::new($false)

$script:Subcommand = ''
$script:Opts = @{}
$script:Flags = @{}
$script:Root = ''
$script:DbPath = ''
$script:DumpPath = ''
$script:RulesPath = ''
$script:Sqlite = ''
$script:Indicator = ''
$script:PayloadDir = ''

$script:ValueOptions = @('project', 'indicator', 'title', 'branch', 'plan-path', 'issue', 'role', 'code', 'reason', 'state',
  'status', 'candidate-tag', 'evidence', 'release-version')
$script:SwitchOptions = @('dry-run', 'json', 'strict', 'check', 'no-fetch', 'strict-git', 'help')

# The ledger_status vocabulary, identical to the CHECK in schema/001-plan.sql. The parser
# refuses anything else by name, so a mistyped stage status cannot reach the row and be
# rejected by a constraint error the caller cannot read.
$script:LedgerStatuses = @('draft', 'under-review', 'awaiting-approval', 'approved', 'in-progress',
  'testing', 'passed', 'release-version-decided', 'merged', 'deployed', 'released', 'abandoned')

$script:IndicatorPattern = '^[A-Z][A-Z0-9]{1,9}$'
$script:FilePattern = '^(?<code>[A-Z][A-Z0-9]{1,9})-(?<num>\d{5})-(?<date>\d{4}-\d{2}-\d{2})-(?<slug>.+)$'
$script:CellPattern = '^(?<code>[A-Z][A-Z0-9]{1,9})-(?<num>\d{5})$'
$script:BranchPattern = '^(?:feat|fix|chore|docs|refactor|perf)/(?<code>[A-Z][A-Z0-9]{1,9})-(?<num>\d{5})'
$script:BranchClaimPattern = '^(?<type>feat|fix|chore|docs|refactor|perf)/(?<code>[A-Z][A-Z0-9]{1,9})-(?<num>\d{5})-(?<slug>[^/\s]+)(?:/(?<slice>[^/\s]+))?$'
$script:PlanPathPattern = '^plans/(?<code>[A-Z][A-Z0-9]{1,9})-(?<num>\d{5})-(?<date>\d{4}-\d{2}-\d{2})-(?<slug>[^/]+\.md)$'

# Table order for the data section. Any table not named here is dumped after these,
# ordered by name, so a future table needs no change to this tool.
$script:DumpOrder = [ordered]@{
  project          = 'indicator'
  indicator_alias  = 'old_code'
  work_item        = 'number'
  allocation_event = 'id'
  deferred_defect  = 'id'
}

# ---------------------------------------------------------------------------
# Output and failure helpers
# ---------------------------------------------------------------------------

function Write-Out {
  param([string]$Message)
  [Console]::Out.WriteLine($Message)
}

function Write-Warn {
  param([string]$Message)
  [Console]::Error.WriteLine("warn: $Message")
}

function Stop-With {
  param([int]$Code, [string]$Message)
  if (-not [string]::IsNullOrEmpty($Message)) { [Console]::Error.WriteLine($Message) }
  throw [System.OperationCanceledException]::new("__plan_code_exit:$Code")
}

function Get-OptValue {
  param([string]$Name, [string]$Default = '')
  if ($script:Opts.ContainsKey($Name)) { return [string]$script:Opts[$Name] }
  return $Default
}

function Test-Flag {
  param([string]$Name)
  if ($script:Flags.ContainsKey($Name)) { return [bool]$script:Flags[$Name] }
  return $false
}

# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

function Parse-CliArgs {
  param([string[]]$Argv)

  if ($null -eq $Argv -or $Argv.Count -eq 0) {
    Stop-With 3 'usage: plan-code.ps1 <init|import|assign|void|status|verify|export> [options] --project <root>'
  }

  $first = [string]$Argv[0]
  if ($first.StartsWith('-')) {
    Stop-With 3 "expected a subcommand, got '$first'"
  }
  $script:Subcommand = $first.ToLowerInvariant()
  if ($script:Subcommand -notin @('init', 'import', 'assign', 'void', 'update', 'status', 'verify', 'export')) {
    Stop-With 3 "unknown subcommand '$first'; expected init, import, assign, void, update, status, verify, or export"
  }

  $i = 1
  while ($i -lt $Argv.Count) {
    $token = [string]$Argv[$i]
    if (-not $token.StartsWith('--')) {
      Stop-With 3 "unexpected argument '$token'"
    }
    $body = $token.Substring(2)
    $inline = $null
    $eq = $body.IndexOf('=')
    if ($eq -ge 0) {
      $inline = $body.Substring($eq + 1)
      $body = $body.Substring(0, $eq)
    }
    $name = $body.ToLowerInvariant()

    if ($script:SwitchOptions -contains $name) {
      if ($null -ne $inline) { Stop-With 3 "option '--$body' does not take a value" }
      $script:Flags[$name] = $true
      $i++
      continue
    }
    if ($script:ValueOptions -notcontains $name) {
      Stop-With 3 "unknown option '--$body'"
    }
    if ($null -eq $inline) {
      if ($i + 1 -ge $Argv.Count) { Stop-With 3 "option '--$body' requires a value" }
      $script:Opts[$name] = [string]$Argv[$i + 1]
      $i += 2
    } else {
      $script:Opts[$name] = $inline
      $i++
    }
  }

  if (Test-Flag 'help') { Show-Usage; Stop-With 0 '' }
}

function Show-Usage {
  Write-Out 'plan-code.ps1 <subcommand> [options] [--project <root>]'
  Write-Out ''
  Write-Out '  init    --indicator <CODE>              create plans/_plan.db, register the indicator, export'
  Write-Out '  import                                  rebuild plans/_plan.db from plans/_plan.sql'
  Write-Out '  export  [--check]                       rewrite plans/_plan.sql from plans/_plan.db'
  Write-Out '  assign  --title <text> --branch <ref> --plan-path <path>'
  Write-Out '          [--role <text>] [--issue <n>] [--dry-run] [--no-fetch] [--strict-git]'
  Write-Out '  void    --code <IND-NNNNN> --reason <text>'
  Write-Out '  update  --code <IND-NNNNN> [--status <stage>] [--candidate-tag <tag>]'
  Write-Out '          [--evidence <path>] [--issue <n>] [--release-version <X.Y.Z>]'
  Write-Out '          [--plan-path <path>]   then run export'
  Write-Out '  status  [--state <committed|voided>] [--json]'
  Write-Out '  verify  [--strict] [--no-fetch] [--strict-git]'
  Write-Out ''
  Write-Out '  exit 0 ok, 1 verification or drift failure, 2 contention, 3 invalid input, 4 git failure'
}

# ---------------------------------------------------------------------------
# Project, dependency and indicator resolution
# ---------------------------------------------------------------------------

function Initialize-Project {
  $project = Get-OptValue 'project' ''
  if ([string]::IsNullOrWhiteSpace($project)) { $project = (Get-Location).Path }
  if (-not (Test-Path -LiteralPath $project -PathType Container)) {
    Stop-With 3 "project root not found: $project"
  }
  $script:Root = (Resolve-Path -LiteralPath $project).ProviderPath
  $script:DbPath = Join-Path $script:Root 'plans/_plan.db'
  $script:DumpPath = Join-Path $script:Root 'plans/_plan.sql'
  $script:RulesPath = Join-Path $script:Root 'plans/PLAN-RULES.md'
  if (-not (Test-Path -LiteralPath (Join-Path $script:Root 'plans') -PathType Container)) {
    Stop-With 3 "directory not found: $(Join-Path $script:Root 'plans')"
  }
}

function Initialize-Sqlite {
  $override = $env:AVRIG_SQLITE3
  if (-not [string]::IsNullOrWhiteSpace($override)) {
    if (-not (Test-Path -LiteralPath $override -PathType Leaf)) {
      Stop-With 3 "AVRIG_SQLITE3 names '$override', which does not exist; install sqlite3 or correct AVRIG_SQLITE3"
    }
    $script:Sqlite = (Resolve-Path -LiteralPath $override).ProviderPath
    return
  }
  $cmd = Get-Command -Name 'sqlite3' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($null -eq $cmd) {
    Stop-With 3 'sqlite3 was not found on PATH; install sqlite3 or set AVRIG_SQLITE3 to the binary'
  }
  $script:Sqlite = $cmd.Source
}

function Get-RulesField {
  # Reads one scalar from the frontmatter of plans/PLAN-RULES.md. Only the frontmatter
  # counts: the file also shows the same keys inside a fenced block, and a second
  # declaration site in code would make the two able to disagree.
  param([string]$Key = 'project_indicator')

  if (-not (Test-Path -LiteralPath $script:RulesPath -PathType Leaf)) { return '' }
  $raw = [IO.File]::ReadAllText($script:RulesPath)
  $lines = $raw -split "\r?\n"
  if ($lines.Count -lt 2) { return '' }
  if ($lines[0].TrimStart([char]0xFEFF).Trim() -cne '---') { return '' }
  $pattern = '^' + [regex]::Escape($Key) + ':\s*(?<value>\S+)\s*$'
  for ($i = 1; $i -lt $lines.Count; $i++) {
    if ($lines[$i].Trim() -ceq '---') { break }
    $m = [regex]::Match($lines[$i], $pattern)
    if ($m.Success) { return $m.Groups['value'].Value }
  }
  return ''
}

function Get-RulesIndicator {
  return (Get-RulesField -Key 'project_indicator')
}

function Assert-IndicatorShape {
  param([string]$Indicator)
  if ($Indicator -cnotmatch $script:IndicatorPattern) {
    Stop-With 3 "invalid indicator '$Indicator': the shape is $($script:IndicatorPattern), uppercase letters and digits, starting with a letter"
  }
}

function Initialize-Indicator {
  $declared = Get-RulesIndicator
  $requested = Get-OptValue 'indicator' ''

  if ([string]::IsNullOrWhiteSpace($requested) -and [string]::IsNullOrWhiteSpace($declared)) {
    Stop-With 3 ('no project indicator: plans/PLAN-RULES.md frontmatter has no project_indicator ' +
      'and --indicator was not given')
  }
  if (-not [string]::IsNullOrWhiteSpace($requested) -and -not [string]::IsNullOrWhiteSpace($declared) -and $requested -cne $declared) {
    Stop-With 3 "indicator mismatch: --indicator is '$requested' but plans/PLAN-RULES.md declares '$declared'"
  }

  $indicator = if ([string]::IsNullOrWhiteSpace($requested)) { $declared } else { $requested }
  Assert-IndicatorShape $indicator
  $script:Indicator = $indicator
}

# ---------------------------------------------------------------------------
# Payload files
# ---------------------------------------------------------------------------

function Get-PayloadDirectory {
  # One directory per process, named with the process id and a random suffix. A shared
  # directory let a temp cleaner, a second checkout, or a concurrent run delete payload
  # files out from under this one, so the isolation is part of the contract rather than
  # tidiness: two runs can no longer remove each other's files.
  if (-not [string]::IsNullOrWhiteSpace($script:PayloadDir)) { return $script:PayloadDir }

  $candidates = @()
  if (-not [string]::IsNullOrWhiteSpace($env:TEMP)) { $candidates += (Join-Path $env:TEMP 'plan-code-payload') }
  if (-not [string]::IsNullOrWhiteSpace($env:TMP)) { $candidates += (Join-Path $env:TMP 'plan-code-payload') }
  $candidates += '/tmp/plan-code-payload'
  $leaf = 'p{0}-{1}' -f $PID, ([guid]::NewGuid().ToString('N').Substring(0, 8))

  foreach ($candidate in $candidates) {
    $full = [IO.Path]::GetFullPath((Join-Path $candidate $leaf))
    # sqlite3's '.parameter set' splits on whitespace, so the path must be space free.
    if ($full -cnotmatch "^[^\s']+$") { continue }
    try {
      New-Item -ItemType Directory -Force -Path $full | Out-Null
      $script:PayloadDir = $full
      return $script:PayloadDir
    } catch {
      continue
    }
  }
  Stop-With 3 'no space free directory is available for the sqlite3 payload; point TEMP at a path without spaces'
}

function New-PayloadFile {
  param([object]$Payload)

  $directory = Get-PayloadDirectory
  $path = Join-Path $directory ('p-' + [guid]::NewGuid().ToString('N') + '.json')
  # The one element array is required: json_each over an object yields one row per
  # member, which breaks the statement. The write is BOM free by construction.
  $json = ConvertTo-Json -InputObject @($Payload) -Compress -Depth 8
  $utf8 = [Text.UTF8Encoding]::new($false)
  try {
    [IO.File]::WriteAllText($path, $json, $utf8)
  } catch {
    # The directory can still vanish between creation and the write. Recreate it once,
    # then report an exit code rather than letting an unhandled .NET exception escape.
    try {
      New-Item -ItemType Directory -Force -Path $directory | Out-Null
      [IO.File]::WriteAllText($path, $json, $utf8)
    } catch {
      Stop-With 3 "the sqlite3 payload file could not be written under $directory`: $($_.Exception.Message)"
    }
  }
  return ($path -replace '\\', '/')
}

function Remove-PayloadFile {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return }
  Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
}

# ---------------------------------------------------------------------------
# sqlite3 and git wrappers
# ---------------------------------------------------------------------------

function Resolve-SqliteExit {
  param($Result)
  if ($Result.Exit -eq 5 -or $Result.Text -match '(?i)database (table )?is locked') { return 2 }
  if ($Result.Text -match '(?i)file is not a database|malformed database') { return 1 }
  return 3
}

function Invoke-Sqlite {
  param([string]$Database, [string[]]$Script)

  # Every invocation carries the busy handler, read or write. A read can lose the lock as
  # easily as a write, and a read without a timeout reports SQLITE_BUSY on the first
  # attempt. This is one half of the contention contract: Resolve-SqliteExit is the other,
  # because a WAL reader under a writer's EXCLUSIVE lock does not block at all, so the
  # timeout alone would not make contention visible.
  $text = ((@('.timeout 5000') + @($Script)) -join "`n") + "`n"
  $raw = @($text | & $script:Sqlite -noheader $Database 2>&1)
  $exit = $LASTEXITCODE
  $lines = @($raw | ForEach-Object {
      if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.ToString() } else { [string]$_ }
    })
  [pscustomobject]@{ Exit = $exit; Lines = $lines; Text = ($lines -join "`n") }
}

function Invoke-SqlitePayload {
  param([string]$Script, [object]$Payload, [string]$Database = '')

  if ([string]::IsNullOrWhiteSpace($Database)) { $Database = $script:DbPath }
  $file = New-PayloadFile $Payload
  try {
    $lines = @('.bail on', '.timeout 5000', ".parameter set :payload '$file'") + @($Script)
    $result = Invoke-Sqlite -Database $Database -Script $lines
    if ($result.Exit -ne 0) {
      Stop-With (Resolve-SqliteExit $result) "sqlite3 failed on $Database`: $($result.Text)"
    }
    return $result
  } finally {
    Remove-PayloadFile $file
  }
}

function Invoke-SqliteScalar {
  param([string]$Script, [object]$Payload = @{}, [string]$Database = '')

  if ([string]::IsNullOrWhiteSpace($Database)) { $Database = $script:DbPath }
  $result = if ($null -eq $Payload) {
    Invoke-Sqlite -Database $Database -Script @($Script)
  } else {
    Invoke-SqlitePayload -Script $Script -Payload $Payload -Database $Database
  }
  $line = @($result.Lines | Where-Object { $_.Trim() -ne '' }) | Select-Object -First 1
  if ($null -eq $line) { return '' }
  return ([string]$line).Trim()
}

function Invoke-Git {
  param([string[]]$GitArgs)

  $raw = @(& git -C $script:Root @GitArgs 2>&1)
  $exit = $LASTEXITCODE
  $lines = @($raw | ForEach-Object {
      if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.ToString() } else { [string]$_ }
    } | Where-Object { $_ -ne '' })
  [pscustomobject]@{ Exit = $exit; Lines = $lines; Text = ($lines -join "`n") }
}

function Test-GitRepository {
  $result = Invoke-Git @('rev-parse', '--git-dir')
  return ($result.Exit -eq 0)
}

function Get-GitRemotes {
  $result = Invoke-Git @('remote')
  if ($result.Exit -ne 0) { return @() }
  return @($result.Lines | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
}

function Get-LocalBranches {
  $result = Invoke-Git @('for-each-ref', 'refs/heads', '--format=%(refname:short)')
  if ($result.Exit -ne 0) { return @() }
  return @($result.Lines | Where-Object { $_ -ne '' })
}

function Test-WorkBranchName {
  param([string]$Name)
  # The project's own taxonomy: a work branch is <type>/<CODE>-<NNNNN>-<slug>, so it is
  # never a long lived branch. `main`, `master`, `develop`, and the like are.
  return ($Name -cmatch '^(?:feat|fix|chore|docs|refactor|perf)/')
}

function Resolve-DefaultBranch {
  # The four step contract. Step 5 is a refusal, never a guess.
  if (-not (Test-GitRepository)) { return '' }

  $remotes = @(Get-GitRemotes)
  $hasOrigin = $remotes -contains 'origin'
  $locals = @(Get-LocalBranches)
  $current = ''
  $head = Invoke-Git @('rev-parse', '--abbrev-ref', 'HEAD')
  if ($head.Exit -eq 0 -and $head.Lines.Count -gt 0) { $current = [string]$head.Lines[0] }

  if (-not $hasOrigin) {
    # A checkout with no origin remote cannot hold a remote number, so the union reads
    # local refs only and no default branch is needed. The caller reports the warning.
    return ''
  }

  # 1. the current branch tracks a remote and is the repository's only long lived branch
  if ($current -ne '' -and $current -cne 'HEAD') {
    $upstreamConfig = Invoke-Git @('config', '--get', "branch.$current.remote")
    if ($upstreamConfig.Exit -eq 0 -and -not [string]::IsNullOrWhiteSpace($upstreamConfig.Text)) {
      $longLived = @($locals | Where-Object { -not (Test-WorkBranchName $_) })
      if ($longLived.Count -eq 1 -and $longLived[0] -ceq $current) { return $current }
    }
  }

  # 2 and 3. origin/HEAD names a branch that exists locally
  $symref = Invoke-Git @('symbolic-ref', '--short', 'refs/remotes/origin/HEAD')
  if ($symref.Exit -eq 0 -and $symref.Lines.Count -gt 0) {
    $name = ([string]$symref.Lines[0]) -replace '^origin/', ''
    if ($locals -ccontains $name) { return $name }
  }

  # 4. exactly one local branch
  if ($locals.Count -eq 1) { return [string]$locals[0] }

  # 5. stop and ask
  Stop-With 3 ("cannot resolve the default branch: origin/HEAD does not name a local branch and " +
    "$($locals.Count) local branches exist ($($locals -join ', ')); record the default branch before allocating")
}

# ---------------------------------------------------------------------------
# Dump loading
# ---------------------------------------------------------------------------

function Invoke-DumpLoad {
  param([string]$Database, [string]$DumpPath, [string]$Trailer = '')

  $full = (Resolve-Path -LiteralPath $DumpPath).ProviderPath -replace '\\', '/'
  $lines = @('.bail on', '.timeout 5000')
  if ($full -cmatch "^[^\s']+$") {
    $lines += ".read '$full'"
  } else {
    # '.read' splits its argument on whitespace, so a path with a space is fed as
    # content on stdin instead. The statements applied are identical.
    $lines += ((@([IO.File]::ReadAllText($DumpPath)) -join "`n") -split "\r?\n")
  }
  if (-not [string]::IsNullOrWhiteSpace($Trailer)) { $lines += $Trailer }
  return (Invoke-Sqlite -Database $Database -Script $lines)
}

function Get-DumpMax {
  param([string]$DumpPath, [string]$Indicator)

  if (-not (Test-Path -LiteralPath $DumpPath -PathType Leaf)) { return 0 }
  $query = "SELECT COALESCE(MAX(number),0) FROM work_item WHERE indicator = '$Indicator';"
  $result = Invoke-DumpLoad -Database ':memory:' -DumpPath $DumpPath -Trailer $query
  if ($result.Exit -ne 0) {
    Stop-With (Resolve-SqliteExit $result) "plans/_plan.sql could not be read: $($result.Text)"
  }
  $line = @($result.Lines | Where-Object { $_.Trim() -match '^\d+$' }) | Select-Object -Last 1
  if ($null -eq $line) { return 0 }
  return [int]([string]$line).Trim()
}

function Get-RemoteDumpMax {
  param([string]$DefaultBranch, [string]$Indicator)

  $ref = "origin/${DefaultBranch}:plans/_plan.sql"
  $show = Invoke-Git @('show', $ref)
  if ($show.Exit -ne 0) {
    return [pscustomobject]@{ Max = 0; Warning = "origin/$DefaultBranch has no plans/_plan.sql; that source contributed nothing" }
  }
  $file = Join-Path (Get-PayloadDirectory) ('d-' + [guid]::NewGuid().ToString('N') + '.sql')
  try {
    $text = ($show.Lines -join "`n") + "`n"
    [IO.File]::WriteAllText($file, $text, [Text.UTF8Encoding]::new($false))
    $max = Get-DumpMax -DumpPath $file -Indicator $Indicator
    return [pscustomobject]@{ Max = $max; Warning = '' }
  } finally {
    Remove-PayloadFile $file
  }
}

# ---------------------------------------------------------------------------
# Git union: five sources
# ---------------------------------------------------------------------------

function Get-GitUnion {
  param([string]$DefaultBranch)

  $warnings = @()
  $hasGit = Test-GitRepository
  $remotes = @()
  if ($hasGit) { $remotes = @(Get-GitRemotes) }
  $hasOrigin = $remotes -contains 'origin'

  if (-not $hasGit) {
    $warnings += 'not a git repository; the git sources were read from the working tree only'
    if (Test-Flag 'strict-git') { Stop-With 4 'git failure: not a git repository (--strict-git)' }
  } else {
    if (-not $hasOrigin) {
      $warnings += "no 'origin' remote; the remote sources contributed nothing"
      if (Test-Flag 'strict-git') { Stop-With 4 "git failure: no 'origin' remote (--strict-git)" }
    } elseif (Test-Flag 'no-fetch') {
      $warnings += '--no-fetch; the git sources were read from cached refs only'
    } elseif ($DefaultBranch -ne '') {
      $fetch = Invoke-Git @('fetch', 'origin', $DefaultBranch, '--quiet')
      if ($fetch.Exit -ne 0) {
        Stop-With 4 "git failure: fetch origin $DefaultBranch did not complete: $($fetch.Text)"
      }
    }
  }

  $numbers = New-Object System.Collections.Generic.List[int]

  $addCandidate = {
    param([string]$Candidate)
    $name = [IO.Path]::GetFileName($Candidate)
    $m = [regex]::Match($name, $script:FilePattern)
    if (-not $m.Success) { $m = [regex]::Match($Candidate, $script:BranchPattern) }
    if (-not $m.Success) { return }
    if ($m.Groups['code'].Value -cne $script:Indicator) { return }
    $numbers.Add([int]$m.Groups['num'].Value)
  }

  # source 4: filenames, remote tree and working tree
  if ($hasGit -and $hasOrigin -and $DefaultBranch -ne '') {
    $verify = Invoke-Git @('rev-parse', '--verify', '--quiet', "refs/remotes/origin/$DefaultBranch")
    if ($verify.Exit -eq 0) {
      $tree = Invoke-Git @('ls-tree', '-r', '--name-only', "origin/$DefaultBranch", '--', 'plans/')
      if ($tree.Exit -eq 0) {
        foreach ($path in $tree.Lines) { & $addCandidate $path }
      }
    } else {
      $warnings += "origin/$DefaultBranch does not exist; the remote tree contributed nothing"
    }
  }

  $plansDir = Join-Path $script:Root 'plans'
  foreach ($file in @(Get-ChildItem -LiteralPath $plansDir -Filter '*.md' -File -ErrorAction SilentlyContinue)) {
    & $addCandidate $file.Name
  }
  $doneDir = Join-Path $plansDir 'done'
  if (Test-Path -LiteralPath $doneDir -PathType Container) {
    foreach ($file in @(Get-ChildItem -LiteralPath $doneDir -Recurse -Filter '*.md' -File -ErrorAction SilentlyContinue)) {
      & $addCandidate $file.Name
    }
  }

  # source 5: branch names, local and remote, with the remote prefix removed
  if ($hasGit) {
    $branches = Invoke-Git @('branch', '--all', '--format=%(refname:short)')
    if ($branches.Exit -eq 0) {
      foreach ($ref in $branches.Lines) {
        $name = [string]$ref
        foreach ($remote in $remotes) {
          if ($name.StartsWith("$remote/", [StringComparison]::Ordinal)) {
            $name = $name.Substring($remote.Length + 1)
            break
          }
        }
        & $addCandidate $name
      }
    }
  }

  [pscustomobject]@{ Numbers = @($numbers); Warnings = $warnings; HasGit = $hasGit }
}

# ---------------------------------------------------------------------------
# Database bootstrap
# ---------------------------------------------------------------------------

function Get-DbVersion {
  if (-not (Test-Path -LiteralPath $script:DbPath)) { return 0 }
  $result = Invoke-Sqlite -Database $script:DbPath -Script @('PRAGMA user_version;')
  if ($result.Exit -ne 0) {
    # A lock is contention, not a corrupt file. Resolve-SqliteExit maps SQLITE_BUSY to 2
    # from the exit code or the message, because sqlite3 exits 1 for a source error and
    # the text is the only reliable signal on that path.
    Stop-With (Resolve-SqliteExit $result) "plans/_plan.db could not be read: $($result.Text)"
  }
  $line = @($result.Lines | Where-Object { $_.Trim() -match '^\d+$' }) | Select-Object -First 1
  if ($null -eq $line) { return 0 }
  return [int]([string]$line).Trim()
}

function Invoke-SchemaApply {
  $asset = Join-Path $PSScriptRoot 'schema/001-plan.sql'
  if (-not (Test-Path -LiteralPath $asset -PathType Leaf)) {
    Stop-With 3 "schema asset not found: $asset"
  }
  $assetUnix = (Resolve-Path -LiteralPath $asset).ProviderPath -replace '\\', '/'
  if ($assetUnix -cnotmatch "^[^\s']+$") {
    Stop-With 3 "the schema asset path contains whitespace or a quote: $assetUnix"
  }
  $scriptText = @('.bail on', '.timeout 5000', ".read '$assetUnix'")
  $result = Invoke-Sqlite -Database $script:DbPath -Script $scriptText
  if ($result.Exit -ne 0) {
    Stop-With (Resolve-SqliteExit $result) "applying $assetUnix failed: $($result.Text)"
  }
}

function Get-ProjectIndicator {
  if (-not (Test-Path -LiteralPath $script:DbPath)) { return '' }
  $tables = Invoke-Sqlite -Database $script:DbPath -Script @(
    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='project';"
  )
  if ($tables.Exit -ne 0) {
    Stop-With (Resolve-SqliteExit $tables) "plans/_plan.db could not be read: $($tables.Text)"
  }
  $countLine = @($tables.Lines | Where-Object { $_.Trim() -match '^\d+$' }) | Select-Object -First 1
  if ($null -eq $countLine) { return '' }
  if ([int](([string]$countLine).Trim()) -lt 1) { return '' }
  return (Invoke-SqliteScalar -Script 'SELECT indicator FROM project LIMIT 1;' -Payload @{})
}

function Initialize-Database {
  $version = Get-DbVersion
  if ($version -gt 1) {
    Stop-With 3 "plans/_plan.db reports user_version $version, newer than this tool's 1; refusing to touch it"
  }
  if ($version -lt 1) {
    Stop-With 3 'plans/_plan.db carries no schema; run import to rebuild it from plans/_plan.sql'
  }

  $existing = Get-ProjectIndicator
  if ($existing -ne '' -and $existing -cne $script:Indicator) {
    Stop-With 3 "plans/_plan.db belongs to indicator '$existing'; refusing to register '$($script:Indicator)'"
  }
  if ($existing -eq '') {
    $projectKey = Split-Path -Leaf $script:Root
    if ([string]::IsNullOrWhiteSpace($projectKey)) { $projectKey = $script:Indicator }
    # A project row exists only once the indicator is confirmed, so a missing
    # indicator_status means frozen. Anything other than "frozen" means it is not.
    $status = Get-RulesField -Key 'indicator_status'
    $frozen = if ([string]::IsNullOrWhiteSpace($status) -or $status -ceq 'frozen') { 1 } else { 0 }
    # repo_root is deliberately NULL: plans/_plan.sql is committed to git, so a machine
    # path such as this one must never enter it. Nothing reads the column.
    $sql = @'
INSERT INTO project (indicator, project_key, repo_root, frozen)
SELECT json_extract(value,'$.indicator'), json_extract(value,'$.project_key'), NULL, json_extract(value,'$.frozen')
  FROM json_each(readfile(:payload))
 WHERE NOT EXISTS (SELECT 1 FROM project);
'@
    Invoke-SqlitePayload -Script $sql -Payload @{
      indicator   = $script:Indicator
      project_key = $projectKey
      frozen      = $frozen
    } | Out-Null
    $existing = Get-ProjectIndicator
    if ($existing -cne $script:Indicator) {
      Stop-With 3 "the project row was not registered; plans/_plan.db reports '$existing'"
    }
  }
  return $version
}

function Get-DbMax {
  param([string]$Database = '')

  if ([string]::IsNullOrWhiteSpace($Database)) { $Database = $script:DbPath }
  if (-not (Test-Path -LiteralPath $Database -PathType Leaf)) { return 0 }
  $sql = @'
SELECT COALESCE(MAX(number),0) FROM work_item
 WHERE indicator = (SELECT json_extract(value,'$.indicator') FROM json_each(readfile(:payload)));
'@
  $value = Invoke-SqliteScalar -Script $sql -Payload @{ indicator = $script:Indicator } -Database $Database
  if ($value -match '^\d+$') { return [int]$value }
  return 0
}

# ---------------------------------------------------------------------------
# Deterministic dump
# ---------------------------------------------------------------------------

function Get-TableNames {
  param([string]$Database = '')

  if ([string]::IsNullOrWhiteSpace($Database)) { $Database = $script:DbPath }
  $result = Invoke-Sqlite -Database $Database -Script @(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
  )
  if ($result.Exit -ne 0) { Stop-With 1 "plans/_plan.db could not be read: $($result.Text)" }
  return @($result.Lines | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
}

function Get-DumpColumns {
  param([string]$Table, [string]$Database = '')

  # table_info omits generated columns, so work_item.code is absent for free and an
  # INSERT can never name it.
  if ([string]::IsNullOrWhiteSpace($Database)) { $Database = $script:DbPath }
  $result = Invoke-Sqlite -Database $Database -Script @(
    "SELECT name FROM pragma_table_info('$($Table.Replace("'", "''"))');"
  )
  if ($result.Exit -ne 0) { Stop-With 1 "column list for '$Table' could not be read: $($result.Text)" }
  return @($result.Lines | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
}

function Get-TableSql {
  param([string]$Type, [string]$Table, [string]$Database = '')

  $quoted = $Table.Replace("'", "''")
  if ([string]::IsNullOrWhiteSpace($Database)) { $Database = $script:DbPath }
  $result = Invoke-Sqlite -Database $Database -Script @(
    "SELECT sql FROM sqlite_master WHERE type='$Type' AND name='$quoted';"
  )
  if ($result.Exit -ne 0) { Stop-With 1 "sqlite_master could not be read: $($result.Text)" }
  $text = (@($result.Lines) -join "`n").Trim()
  return $text
}

function Get-ObjectSql {
  param([string]$Name, [string]$Database = '')

  if ([string]::IsNullOrWhiteSpace($Database)) { $Database = $script:DbPath }
  $quoted = $Name.Replace("'", "''")
  $result = Invoke-Sqlite -Database $Database -Script @(
    "SELECT sql FROM sqlite_master WHERE name='$quoted' AND sql IS NOT NULL;"
  )
  if ($result.Exit -ne 0) { Stop-With 1 "sqlite_master could not be read: $($result.Text)" }
  return ((@($result.Lines) -join "`n").Trim())
}

function Get-DumpText {
  param([string]$Database = '')

  if ([string]::IsNullOrWhiteSpace($Database)) { $Database = $script:DbPath }
  if (-not (Test-Path -LiteralPath $Database -PathType Leaf)) {
    Stop-With 3 'plans/_plan.db not found; run import or init before exporting'
  }

  $versionResult = Invoke-Sqlite -Database $Database -Script @('PRAGMA user_version;')
  if ($versionResult.Exit -ne 0) { Stop-With 1 "plans/_plan.db could not be read: $($versionResult.Text)" }
  $versionLine = @($versionResult.Lines | Where-Object { $_.Trim() -match '^\d+$' }) | Select-Object -First 1
  if ($null -eq $versionLine) { Stop-With 3 'plans/_plan.db reports no user_version' }
  $version = [int]([string]$versionLine).Trim()

  $tables = @(Get-TableNames -Database $Database)

  $out = New-Object System.Collections.Generic.List[string]
  $out.Add('-- plans/_plan.sql')
  $out.Add('-- Generated by plan-code.ps1 export from plans/_plan.db. Do not edit by hand.')
  $out.Add('-- Apply with: sqlite3 plans/_plan.db ".read plans/_plan.sql"')
  $out.Add("PRAGMA user_version = $version;")
  $out.Add('BEGIN TRANSACTION;')
  $out.Add('')

  # Schema first, ordered by name.
  foreach ($table in $tables) {
    $sql = Get-TableSql -Type 'table' -Table $table -Database $Database
    if ([string]::IsNullOrWhiteSpace($sql)) { Stop-With 1 "sqlite_master returned no CREATE TABLE for '$table'" }
    $sql = ($sql -replace "`r`n", "`n").TrimEnd()
    $out.Add("$sql;")
    $out.Add('')
  }

  # Then data, in the pinned order, one INSERT per statement with an explicit column list.
  $ordered = New-Object System.Collections.Generic.List[string]
  foreach ($table in $script:DumpOrder.Keys) {
    if ($tables -ccontains $table) { $ordered.Add($table) }
  }
  foreach ($table in $tables) {
    if (-not $ordered.Contains($table)) { $ordered.Add($table) }
  }

  foreach ($table in $ordered) {
    $columns = @(Get-DumpColumns -Table $table -Database $Database)
    if ($columns.Count -eq 0) { continue }
    $order = $script:DumpOrder[$table]
    if ($null -eq $order) { $order = 'rowid' }
    $columnList = ($columns -join ',').Replace("'", "''")
    $quoted = $table.Replace('"', '""')
    $values = ($columns | ForEach-Object { "quote($_)" }) -join " || ',' || "
    $query = "SELECT 'INSERT INTO ""$quoted"" ($columnList) VALUES (' || $values || ');'" +
      " FROM ""$quoted"" ORDER BY $order;"
    $result = Invoke-Sqlite -Database $Database -Script @($query)
    if ($result.Exit -ne 0) { Stop-With 1 "rows of '$table' could not be read: $($result.Text)" }
    $block = (@($result.Lines) -join "`n").Trim()
    if ($block -ne '') {
      $out.Add($block)
      $out.Add('')
    }
  }

  # Indexes and triggers last, so a load never fires an append-only trigger over
  # rows that are still arriving. A trigger body carries its own semicolons, so each
  # object is fetched whole by name rather than read out of a single result set.
  $objectNames = Invoke-Sqlite -Database $Database -Script @(
    "SELECT name FROM sqlite_master WHERE type IN ('index','trigger') AND sql IS NOT NULL ORDER BY name;"
  )
  if ($objectNames.Exit -ne 0) { Stop-With 1 "indexes and triggers could not be read: $($objectNames.Text)" }
  foreach ($objectName in @($objectNames.Lines | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })) {
    $sql = Get-ObjectSql -Name $objectName -Database $Database
    if ([string]::IsNullOrWhiteSpace($sql)) { Stop-With 1 "sqlite_master returned no definition for '$objectName'" }
    $sql = ($sql -replace "`r`n", "`n").TrimEnd()
    $out.Add("$sql;")
    $out.Add('')
  }

  $out.Add('COMMIT;')
  return (($out -join "`n") + "`n")
}

function Read-DumpOnDisk {
  param([string]$Path)

  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
  $text = [IO.File]::ReadAllText($Path)
  if ($text.Length -gt 0 -and $text[0] -eq [char]0xFEFF) { $text = $text.Substring(1) }
  return ($text -replace "`r`n", "`n")
}

# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

$script:SelectWorkItemsSql = @'
SELECT json_group_array(json_object(
  'code', code,
  'number', number,
  'indicator', indicator,
  'state', state,
  'title', title,
  'created_on', created_on,
  'repos', repos,
  'claiming_branch', claiming_branch,
  'plan_path', plan_path,
  'issue_number', issue_number,
  'issue_url', issue_url,
  'evidence_path', evidence_path,
  'ledger_status', ledger_status,
  'candidate_tags', candidate_tags,
  'release_version', release_version,
  'voided_at', voided_at,
  'voided_reason', voided_reason,
  'assigned_at', assigned_at,
  'committed_at', committed_at,
  'owner_role', owner_role,
  'actor_host', actor_host,
  'actor_user', actor_user))
FROM (SELECT * FROM work_item
       WHERE indicator = (SELECT json_extract(value,'$.indicator') FROM json_each(readfile(:payload)))
       ORDER BY number);
'@

function Get-WorkItemRows {
  if (-not (Test-Path -LiteralPath $script:DbPath -PathType Leaf)) { return @() }
  $result = Invoke-SqlitePayload -Script $script:SelectWorkItemsSql -Payload @{ indicator = $script:Indicator }
  $text = (@($result.Lines | Where-Object { $_.Trim() -ne '' }) -join "`n").Trim()
  if ([string]::IsNullOrWhiteSpace($text)) {
    Stop-With 1 'plans/_plan.db returned no result for the work item query'
  }
  try {
    $data = $text | ConvertFrom-Json
  } catch {
    Stop-With 1 "plans/_plan.db returned unparseable rows: $text"
  }
  if ($null -eq $data) { return @() }
  return @($data)
}

function Invoke-Init {
  Initialize-Project
  Initialize-Sqlite
  Initialize-Indicator

  if (Test-Path -LiteralPath $script:DumpPath -PathType Leaf) {
    Stop-With 3 ('plans/_plan.sql already exists, so this project has a durable record; ' +
      'run import to rebuild plans/_plan.db from it instead of initialising over it')
  }

  # The newer version guard runs before the DDL, not inside Initialize-Database, because
  # the schema asset ends with "PRAGMA user_version = 1": applying it first would rewrite
  # a newer marker to 1 and the guard would then read this tool's own version. A newer
  # database is refused before a single statement of the asset is applied.
  $prior = Get-DbVersion
  if ($prior -gt 1) {
    Stop-With 3 "plans/_plan.db reports user_version $prior, newer than this tool's 1; refusing to touch it"
  }

  Invoke-SchemaApply
  $version = Get-DbVersion
  if ($version -ne 1) { Stop-With 3 "the schema asset did not set user_version to 1 (got $version)" }

  Initialize-Database | Out-Null

  $text = Get-DumpText
  [IO.File]::WriteAllText($script:DumpPath, $text, [Text.UTF8Encoding]::new($false))

  $rows = @(Get-WorkItemRows)
  Write-Out "init: plans/_plan.db created for $($script:Indicator) and plans/_plan.sql exported ($($rows.Count) row(s))"
  return 0
}

function Invoke-Import {
  Initialize-Project
  Initialize-Sqlite

  if (-not (Test-Path -LiteralPath $script:DumpPath -PathType Leaf)) {
    Stop-With 3 ("plans/_plan.sql not found at $($script:DumpPath); a project with no dump has never " +
      'allocated anything, so run init (with --indicator) instead of import')
  }

  foreach ($suffix in @('', '-wal', '-shm')) {
    $path = $script:DbPath + $suffix
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
  }

  $result = Invoke-DumpLoad -Database $script:DbPath -DumpPath $script:DumpPath
  if ($result.Exit -ne 0) {
    Stop-With (Resolve-SqliteExit $result) "import failed while applying plans/_plan.sql: $($result.Text)"
  }

  # The dump carries the schema and the rows, not the journal mode, so re-establish it.
  $journal = Invoke-Sqlite -Database $script:DbPath -Script @('PRAGMA journal_mode = WAL;')
  if ($journal.Exit -ne 0) {
    Stop-With (Resolve-SqliteExit $journal) "import applied plans/_plan.sql but WAL could not be enabled: $($journal.Text)"
  }

  $tables = @(Get-TableNames)
  $counts = New-Object System.Collections.Generic.List[string]
  $total = 0
  foreach ($table in $tables) {
    $quoted = $table.Replace('"', '""')
    $value = Invoke-SqliteScalar -Script "SELECT COUNT(*) FROM ""$quoted"";" -Payload $null -Database $script:DbPath
    $n = if ($value -match '^\d+$') { [int]$value } else { 0 }
    $total += $n
    $counts.Add("$table=$n")
  }

  Write-Out "import: rebuilt plans/_plan.db from plans/_plan.sql, $total row(s): $($counts -join ' ')"
  return 0
}

function Invoke-Export {
  Initialize-Project
  Initialize-Sqlite

  if (-not (Test-Path -LiteralPath $script:DbPath -PathType Leaf)) {
    Stop-With 3 'plans/_plan.db not found; run import to rebuild it from plans/_plan.sql before exporting'
  }

  $expected = Get-DumpText
  $actual = Read-DumpOnDisk -Path $script:DumpPath

  if (Test-Flag 'check') {
    if ($null -eq $actual) {
      Write-Out 'export --check: plans/_plan.sql is absent and export would create it'
      return 1
    }
    if ($actual -ceq $expected) {
      Write-Out 'export --check: plans/_plan.sql matches plans/_plan.db'
      return 0
    }
    Write-Out 'export --check: plans/_plan.sql and plans/_plan.db disagree; nothing was written'
    return 1
  }

  if ($null -ne $actual -and $actual -ceq $expected) {
    Write-Out 'export: no change'
    return 0
  }

  [IO.File]::WriteAllText($script:DumpPath, $expected, [Text.UTF8Encoding]::new($false))
  $lines = ([regex]::Matches($expected, "`n")).Count
  Write-Out "export: wrote plans/_plan.sql ($lines line(s))"
  return 0
}

function Invoke-Void {
  Initialize-Project
  Initialize-Sqlite
  Initialize-Indicator

  $code = Get-OptValue 'code' ''
  $m = [regex]::Match($code, $script:CellPattern)
  if (-not $m.Success) {
    Stop-With 3 "invalid --code '$code': the shape is <CODE>-<NNNNN>"
  }
  if ($m.Groups['code'].Value -cne $script:Indicator) {
    Stop-With 3 "invalid --code '$code': it belongs to another project indicator"
  }
  $number = [int]$m.Groups['num'].Value

  $reason = Get-OptValue 'reason' ''
  if ([string]::IsNullOrWhiteSpace($reason)) { Stop-With 3 'invalid --reason: it must not be empty' }

  if (-not (Test-Path -LiteralPath $script:DbPath -PathType Leaf)) {
    Stop-With 3 'plans/_plan.db not found; run import first'
  }
  Initialize-Database | Out-Null

  $sql = @'
PRAGMA busy_timeout = 5000;
BEGIN IMMEDIATE;

SELECT 'prior=' || state || '|reason=' || COALESCE(voided_reason,'')
  FROM work_item
 WHERE indicator = json_extract(readfile(:payload),'$[0].indicator')
   AND number = CAST(json_extract(readfile(:payload),'$[0].number') AS INTEGER);

UPDATE work_item
   SET state = 'voided',
       voided_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'),
       voided_reason = json_extract(readfile(:payload),'$[0].reason')
 WHERE indicator = json_extract(readfile(:payload),'$[0].indicator')
   AND number = CAST(json_extract(readfile(:payload),'$[0].number') AS INTEGER)
   AND state = 'committed';

INSERT INTO allocation_event (indicator, number, event, actor_role, actor_host, actor_user, detail)
SELECT w.indicator, w.number, 'void', w.owner_role, w.actor_host, w.actor_user,
       'voided: ' || COALESCE(w.voided_reason,'')
  FROM work_item w
 WHERE w.indicator = json_extract(readfile(:payload),'$[0].indicator')
   AND w.number = CAST(json_extract(readfile(:payload),'$[0].number') AS INTEGER)
   AND w.state = 'voided'
   AND NOT EXISTS (
       SELECT 1 FROM allocation_event e
        WHERE e.event = 'void' AND e.indicator = w.indicator AND e.number = w.number);

COMMIT;

SELECT code, number, state FROM work_item
 WHERE indicator = json_extract(readfile(:payload),'$[0].indicator')
   AND number = CAST(json_extract(readfile(:payload),'$[0].number') AS INTEGER);
'@

  $result = Invoke-SqlitePayload -Script $sql -Payload @{
    indicator = $script:Indicator
    number    = $number
    reason    = $reason
  }

  $prior = @($result.Lines | Where-Object { $_.StartsWith('prior=') }) | Select-Object -First 1
  if ($null -eq $prior) {
    Stop-With 3 "unknown work item $code"
  }
  if ($prior -ceq 'prior=voided') {
    Stop-With 3 "$code is already voided; a burned number is never reissued"
  }
  $final = [regex]::Match($result.Text, "(?m)^$([regex]::Escape($code))\|$number\|(?<state>[a-z]+)\s*$")
  if (-not $final.Success -or $final.Groups['state'].Value -cne 'voided') {
    Stop-With 3 "void did not take effect on $code`: $($result.Text)"
  }
  Write-Out (ConvertTo-Json -InputObject ([ordered]@{ code = $code; number = $number; state = 'voided' }) -Compress)
  return 0
}

function Get-IssueUrl {
  # The issue URL that --issue implies, derived from origin. A non GitHub origin (a
  # fixture's local bare repository, or no remote at all) yields an empty string, and the
  # column is then left as it was rather than filled with a guess.
  param([int]$Issue)

  $remote = Invoke-Git @('remote', 'get-url', 'origin')
  if ($remote.Exit -ne 0 -or $remote.Lines.Count -eq 0) { return '' }
  $url = ([string]$remote.Lines[0]).Trim()
  if ($url -cmatch '^https?://[^/]*github\.com/(?<owner>[^/]+)/(?<repo>[^/]+?)(?:\.git)?/?$') {
    return ('https://github.com/{0}/{1}/issues/{2}' -f $Matches['owner'], $Matches['repo'], $Issue)
  }
  if ($url -cmatch '^git@github\.com:(?<owner>[^/]+)/(?<repo>[^/]+?)(?:\.git)?$') {
    return ('https://github.com/{0}/{1}/issues/{2}' -f $Matches['owner'], $Matches['repo'], $Issue)
  }
  return ''
}

$script:UpdateStatement = @'
WITH payload AS (
  SELECT value AS v FROM json_each(readfile(:payload))
),
target AS (
  SELECT v,
         json_extract(v,'$.indicator') AS ind,
         CAST(json_extract(v,'$.number') AS INTEGER) AS num
    FROM payload
)
-- Only the delivery columns are written, and only the ones the caller named: an
-- absent field reaches the column as NULL from json_extract and COALESCE keeps the stored
-- value. indicator, number, and state are not in this SET list at all, so no flag can
-- reach them, and 'state = committed' means a voided row is never touched.
UPDATE work_item
   SET ledger_status   = COALESCE(json_extract((SELECT v FROM target),'$.status'),          ledger_status),
       candidate_tags  = COALESCE(json_extract((SELECT v FROM target),'$.candidate_tag'),   candidate_tags),
       evidence_path   = COALESCE(json_extract((SELECT v FROM target),'$.evidence'),        evidence_path),
       issue_number    = COALESCE(CAST(json_extract((SELECT v FROM target),'$.issue') AS INTEGER), issue_number),
       issue_url       = COALESCE(NULLIF(json_extract((SELECT v FROM target),'$.issue_url'), ''), issue_url),
       release_version = COALESCE(json_extract((SELECT v FROM target),'$.release_version'), release_version),
       plan_path       = COALESCE(json_extract((SELECT v FROM target),'$.plan_path'),       plan_path)
 WHERE indicator = (SELECT ind FROM target)
   AND number    = (SELECT num FROM target)
   AND state     = 'committed';

-- changes() is the row count of the UPDATE immediately above, so an unknown code or a
-- voided row writes no event: the record only exists when the row actually changed.
INSERT INTO allocation_event (indicator, number, event, actor_role, actor_host, actor_user, detail)
SELECT w.indicator, w.number, 'update', w.owner_role,
       json_extract(readfile(:payload),'$[0].host'),
       json_extract(readfile(:payload),'$[0].user'),
       json_extract(readfile(:payload),'$[0].detail')
  FROM work_item w
 WHERE w.indicator = json_extract(readfile(:payload),'$[0].indicator')
   AND w.number    = CAST(json_extract(readfile(:payload),'$[0].number') AS INTEGER)
   AND w.state     = 'committed'
   AND changes() > 0;
'@

function Invoke-Update {
  Initialize-Project
  Initialize-Sqlite
  Initialize-Indicator

  $code = Get-OptValue 'code' ''
  $m = [regex]::Match($code, $script:CellPattern)
  if (-not $m.Success) {
    Stop-With 3 "invalid --code '$code': the shape is <CODE>-<NNNNN>"
  }
  if ($m.Groups['code'].Value -cne $script:Indicator) {
    Stop-With 3 "invalid --code '$code': it belongs to another project indicator"
  }
  $number = [int]$m.Groups['num'].Value

  # Refused by name, before anything else, so a caller learns which column is protected
  # rather than getting a generic "nothing to update". --state and --indicator are shared
  # with other subcommands and would otherwise parse and be silently ignored.
  foreach ($forbidden in @('state', 'indicator', 'number', 'assigned_at', 'committed_at', 'voided_at', 'voided_reason')) {
    if ($script:Opts.ContainsKey($forbidden)) {
      Stop-With 3 ("invalid option '--$forbidden': indicator, number, state, assigned_at, " +
        'committed_at, voided_at, and voided_reason are not updatable')
    }
  }

  # Option name, payload key, column name, allowed values. An absent option leaves the
  # column alone; a present but empty one is a caller mistake, because a clear is not
  # something this tool offers.
  $fields = [ordered]@{}
  $changed = New-Object System.Collections.Generic.List[string]
  foreach ($pair in @(
      @('status',          'status',          'ledger_status',   $script:LedgerStatuses),
      @('candidate-tag',   'candidate_tag',   'candidate_tags',  $null),
      @('evidence',        'evidence',        'evidence_path',   $null),
      @('release-version', 'release_version', 'release_version', $null))) {
    $option = $pair[0]
    if (-not $script:Opts.ContainsKey($option)) { continue }
    $value = [string]$script:Opts[$option]
    if ([string]::IsNullOrWhiteSpace($value)) {
      Stop-With 3 "invalid --$option`: it must not be empty"
    }
    $allowed = $pair[3]
    if ($null -ne $allowed -and $allowed -notcontains $value) {
      Stop-With 3 "invalid --$option '$value': expected one of $($allowed -join ', ')"
    }
    $fields[$pair[1]] = $value
    $changed.Add($pair[2])
  }

  if ($script:Opts.ContainsKey('issue')) {
    $issueText = [string]$script:Opts['issue']
    if ($issueText -cnotmatch '^[1-9][0-9]{0,8}$') {
      Stop-With 3 "invalid --issue '$issueText': it must be a positive integer"
    }
    $issue = [int]$issueText
    $fields['issue'] = $issue
    $changed.Add('issue_number')
    $issueUrl = Get-IssueUrl -Issue $issue
    if ($issueUrl -ne '') {
      $fields['issue_url'] = $issueUrl
      $changed.Add('issue_url')
    }
  }

  if ($script:Opts.ContainsKey('plan-path')) {
    $fields['plan_path'] = Assert-ExistingPlanPath -Value ([string]$script:Opts['plan-path']) -Code $code
    $changed.Add('plan_path')
  }

  if ($changed.Count -eq 0) {
    Stop-With 3 ('nothing to update: give --status, --candidate-tag, --evidence, --issue, ' +
      '--plan-path, or --release-version')
  }
  # Sorted so the event detail and the reported list read the same on every run: the
  # collection order would otherwise follow option parsing.
  $changed = @($changed | Sort-Object)

  if (-not (Test-Path -LiteralPath $script:DbPath -PathType Leaf)) {
    Stop-With 3 'plans/_plan.db not found; run import first'
  }
  Initialize-Database | Out-Null

  $payload = [ordered]@{
    indicator       = $script:Indicator
    number          = $number
    host            = [Environment]::MachineName
    user            = [Environment]::UserName
    detail          = 'updated: ' + ($changed -join ', ')
    status          = $null
    candidate_tag   = $null
    evidence        = $null
    issue           = $null
    issue_url       = $null
    release_version = $null
    plan_path       = $null
  }
  foreach ($key in $fields.Keys) { $payload[$key] = $fields[$key] }

  $sql = @'
PRAGMA busy_timeout = 5000;
BEGIN IMMEDIATE;

SELECT 'prior=' || state FROM work_item
 WHERE indicator = json_extract(readfile(:payload),'$[0].indicator')
   AND number = CAST(json_extract(readfile(:payload),'$[0].number') AS INTEGER);

'@ + $script:UpdateStatement + @'
COMMIT;

-- The row comes back as one JSON object rather than as delimited text. A value the caller
-- supplies can contain a newline or a pipe, and either one splits a text row into lines
-- that no longer parse, which turns a successful write into a reported refusal. JSON
-- escapes both, and ConvertFrom-Json restores the exact text.
SELECT 'ROW|' || json_object(
         'code',            code,
         'number',          number,
         'state',           state,
         'ledger_status',   COALESCE(ledger_status,''),
         'candidate_tags',  COALESCE(candidate_tags,''),
         'evidence_path',   COALESCE(evidence_path,''),
         'issue_number',    COALESCE(issue_number,''),
         'issue_url',       COALESCE(issue_url,''),
         'release_version', COALESCE(release_version,''))
  FROM work_item
 WHERE indicator = json_extract(readfile(:payload),'$[0].indicator')
   AND number = CAST(json_extract(readfile(:payload),'$[0].number') AS INTEGER);
'@

  $result = Invoke-SqlitePayload -Script $sql -Payload $payload

  $prior = @($result.Lines | Where-Object { $_.StartsWith('prior=') }) | Select-Object -First 1
  if ($null -eq $prior) {
    Stop-With 3 "unknown work item $code"
  }
  if ($prior -ceq 'prior=voided') {
    Stop-With 3 "$code is voided; a burned number is never changed"
  }

  $rowLine = @($result.Lines | Where-Object { $_.StartsWith('ROW|') }) | Select-Object -First 1
  if ($null -eq $rowLine) {
    Stop-With 3 "update did not return the row for $code`: $($result.Text)"
  }
  try {
    $row = ([string]$rowLine).Substring(4) | ConvertFrom-Json
  } catch {
    Stop-With 3 "update returned an unreadable row: $rowLine"
  }

  $out = [ordered]@{
    code            = [string]$row.code
    number          = [int]$row.number
    state           = [string]$row.state
    ledger_status   = [string]$row.ledger_status
    candidate_tags  = [string]$row.candidate_tags
    evidence_path   = [string]$row.evidence_path
    issue_number    = if ([string]$row.issue_number -eq '') { $null } else { [int]$row.issue_number }
    issue_url       = [string]$row.issue_url
    release_version = [string]$row.release_version
    changed         = @($changed)
  }
  Write-Out (ConvertTo-Json -InputObject $out -Compress)
  # The cycle is update then export, so the dump is stale from here until export runs.
  # verify --strict would report the same drift; the reminder just saves a round trip.
  Write-Warn 'plans/_plan.sql is now stale; run export to record this update'
  return 0
}

function Invoke-Status {
  Initialize-Project
  Initialize-Sqlite
  Initialize-Indicator

  if (Test-Path -LiteralPath $script:DbPath -PathType Leaf) {
    Initialize-Database | Out-Null
  }

  $rows = @()
  if (Test-Path -LiteralPath $script:DbPath -PathType Leaf) { $rows = @(Get-WorkItemRows) }

  $stateFilter = Get-OptValue 'state' ''
  if ($stateFilter -ne '') {
    if ($stateFilter -cnotin @('committed', 'voided')) {
      Stop-With 3 "invalid --state '$stateFilter': expected committed or voided"
    }
    $rows = @($rows | Where-Object { $_.state -ceq $stateFilter })
  }

  if (Test-Flag 'json') {
    $output = @()
    foreach ($row in $rows) {
      $output += [ordered]@{
        code            = $row.code
        number          = [int]$row.number
        indicator       = $row.indicator
        state           = $row.state
        title           = $row.title
        created_on      = $row.created_on
        repos           = $row.repos
        owner_role      = $row.owner_role
        claiming_branch = $row.claiming_branch
        plan_path       = $row.plan_path
        issue_number    = if ($null -eq $row.issue_number) { $null } else { [int]$row.issue_number }
        issue_url       = $row.issue_url
        evidence_path   = $row.evidence_path
        ledger_status   = $row.ledger_status
        candidate_tags  = $row.candidate_tags
        release_version = $row.release_version
        assigned_at     = $row.assigned_at
        committed_at    = $row.committed_at
        voided_at       = $row.voided_at
        voided_reason   = $row.voided_reason
        actor_host      = $row.actor_host
        actor_user      = $row.actor_user
      }
    }
    Write-Out (ConvertTo-Json -InputObject @($output) -Compress -Depth 5)
    return 0
  }

  if ($rows.Count -eq 0) {
    Write-Out "status: no work items for $($script:Indicator)"
    return 0
  }

  $format = '{0,-12} {1,-10} {2,-12} {3,-46} {4}'
  Write-Out ($format -f 'CODE', 'STATE', 'CREATED', 'TITLE', 'CLAIMING BRANCH')
  foreach ($row in $rows) {
    $title = [string]$row.title
    if ($title.Length -gt 46) { $title = $title.Substring(0, 43) + '...' }
    $branch = [string]$row.claiming_branch
    if ($null -eq $row.claiming_branch) { $branch = '-' }
    Write-Out ($format -f $row.code, $row.state, $row.created_on, $title, $branch)
    if ($row.state -ceq 'voided') {
      Write-Out ('{0,-12} voided_at {1}: {2}' -f '', $row.voided_at, $row.voided_reason)
    }
  }
  return 0
}

function Invoke-Verify {
  Initialize-Project
  Initialize-Sqlite

  $findings = New-Object System.Collections.Generic.List[string]

  $declared = Get-RulesIndicator
  $requested = Get-OptValue 'indicator' ''
  $indicator = if (-not [string]::IsNullOrWhiteSpace($requested)) { $requested }
  elseif (-not [string]::IsNullOrWhiteSpace($declared)) { $declared }
  else { Get-ProjectIndicator }

  if ([string]::IsNullOrWhiteSpace($indicator)) {
    $findings.Add('no project indicator: plans/PLAN-RULES.md declares no project_indicator and plans/_plan.db has no project row')
  } elseif ($indicator -cnotmatch $script:IndicatorPattern) {
    $findings.Add("invalid indicator '$indicator': the shape is $($script:IndicatorPattern)")
  } else {
    $script:Indicator = $indicator
  }

  $dbExists = Test-Path -LiteralPath $script:DbPath -PathType Leaf
  if (-not $dbExists) {
    $findings.Add('plans/_plan.db is absent; run import to rebuild it from plans/_plan.sql')
  } else {
    if ($script:Indicator -ne '') { Initialize-Database | Out-Null }

    $expected = Get-DumpText
    $actual = Read-DumpOnDisk -Path $script:DumpPath
    if ($null -eq $actual) {
      $findings.Add('plans/_plan.sql is absent; run export so the durable record matches the database')
    } elseif ($actual -cne $expected) {
      $findings.Add('plans/_plan.sql does not match plans/_plan.db; run export')
    }
  }

  $rows = @()
  if ($dbExists -and $script:Indicator -ne '') { $rows = @(Get-WorkItemRows) }
  $known = @{}
  foreach ($row in $rows) { $known[[int]$row.number] = $true }

  # The pointer is checked in both directions. The union check above proves that every
  # number claimed by a file or a branch has a row; this proves that every row names a file
  # that is really there. Without it a row can point at a draft name that the approval
  # rename left behind, and the drift is invisible.
  $plansDir = Join-Path $script:Root 'plans'
  foreach ($row in @($rows | Where-Object { $_.state -ceq 'committed' })) {
    $code = [string]$row.code
    $path = [string]$row.plan_path
    if ([string]::IsNullOrWhiteSpace($path)) {
      $findings.Add("${code}: plans/_plan.db holds no plan_path for a committed row (fix with update --code $code --plan-path <real path>)")
      continue
    }
    $base = Split-Path -Leaf ([string]$path).Replace('\', '/')
    $present = (Test-Path -LiteralPath (Join-Path $plansDir $base) -PathType Leaf) -or
               (Test-Path -LiteralPath (Join-Path $plansDir "done/$base") -PathType Leaf)
    if (-not $present) {
      $findings.Add("${code}: plans/_plan.db names a plan file that is not there: $path (fix with update --code $code --plan-path <real path>)")
    }
  }

  if ($script:Indicator -ne '' -and $dbExists) {
    $defaultBranch = Resolve-DefaultBranch
    $union = Get-GitUnion -DefaultBranch $defaultBranch
    foreach ($warning in $union.Warnings) { Write-Warn $warning }
    foreach ($number in @($union.Numbers | Select-Object -Unique)) {
      if (-not $known.ContainsKey($number)) {
        $code = '{0}-{1:D5}' -f $script:Indicator, $number
        $findings.Add("$code is claimed by a plan file or a branch but has no work_item row; run import")
      }
    }
  }

  $dbIndicator = if ($dbExists) { Get-ProjectIndicator } else { '' }
  if ([string]::IsNullOrWhiteSpace($declared)) {
    $findings.Add('plans/PLAN-RULES.md is absent or declares no project_indicator')
  } elseif ($dbIndicator -ne '' -and $declared -cne $dbIndicator) {
    $findings.Add("plans/PLAN-RULES.md declares '$declared' but plans/_plan.db records '$dbIndicator'")
  }

  if ($findings.Count -eq 0) {
    Write-Out "verify: ok, $($rows.Count) row(s) in plans/_plan.db agree with plans/_plan.sql, PLAN-RULES.md, and the git union"
    return 0
  }

  foreach ($finding in $findings) { Write-Out "drift: $finding" }
  Write-Out "verify: $($findings.Count) drift finding(s)"
  if (Test-Flag 'strict') { return 1 }
  return 0
}

function Get-ProspectiveNumber {
  param([int]$DbMax, [int]$DumpMax, [int]$RemoteDumpMax, [int[]]$Numbers)

  $filenameMax = 0
  foreach ($n in $Numbers) { if ($n -gt $filenameMax) { $filenameMax = $n } }
  $highest = $DbMax
  foreach ($n in @($DumpMax, $RemoteDumpMax, $filenameMax)) { if ($n -gt $highest) { $highest = $n } }
  return [pscustomobject]@{
    Number        = $highest + 1
    DbMax         = $DbMax
    DumpMax       = $DumpMax
    RemoteDumpMax = $RemoteDumpMax
    ClaimMax      = $filenameMax
  }
}

function Assert-BranchInput {
  param([string]$Template, [int]$Number)

  $code = '{0}-{1:D5}' -f $script:Indicator, $Number
  $final = $Template.Replace('{code}', $code)
  $m = [regex]::Match($final, $script:BranchClaimPattern)
  if (-not $m.Success) {
    Stop-With 3 "invalid --branch '$final': the shape is <type>/<CODE>-<NNNNN>-<slug>, optionally followed by /<slice>"
  }
  if ($m.Groups['code'].Value -cne $script:Indicator) {
    Stop-With 3 "invalid --branch '$final': the code belongs to indicator '$($m.Groups['code'].Value)', not '$($script:Indicator)'"
  }
  $named = [int]$m.Groups['num'].Value
  if ($named -ne $Number) {
    Stop-With 3 "invalid --branch '$final': it names number $('{0:D5}' -f $named) but this assignment is $code"
  }
  # The template goes to the statement unsubstituted. The number written is computed
  # inside the write transaction and can exceed this candidate under contention, so a
  # substitution made here would carry a stale code and fail ck_branch_carries_code.
  # The statement substitutes from the number it computes, then proves the stored text.
  return $Template
}

function Assert-PlanPathInput {
  param([string]$Template, [int]$Number)

  $code = '{0}-{1:D5}' -f $script:Indicator, $Number
  $final = $Template.Replace('{code}', $code)
  if ($final -cmatch '(^|/)\.\.(/|$)') {
    Stop-With 3 "invalid --plan-path '$final': it carries a '..' segment"
  }
  $m = [regex]::Match($final, $script:PlanPathPattern)
  if (-not $m.Success) {
    Stop-With 3 "invalid --plan-path '$final': the shape is plans/<CODE>-<NNNNN>-<YYYY-MM-DD>-<slug>.md"
  }
  if ($m.Groups['code'].Value -cne $script:Indicator) {
    Stop-With 3 "invalid --plan-path '$final': the code belongs to indicator '$($m.Groups['code'].Value)', not '$($script:Indicator)'"
  }
  $named = [int]$m.Groups['num'].Value
  if ($named -ne $Number) {
    Stop-With 3 "invalid --plan-path '$final': it names number $('{0:D5}' -f $named) but this assignment is $code"
  }
  # Unsubstituted for the same reason as --branch: the statement substitutes the number
  # it actually wrote, and its guard proves the stored path carries that number.
  return $Template
}

# The corrective twin of Assert-PlanPathInput: that one checks the shape a caller may
# propose at assignment, while this one checks a path that is already supposed to be real,
# so it also proves the file is on disk. Assert-PlanPathInput stays free of the existence
# check because assign runs before the rename, when the final name legitimately does not
# exist yet.
function Assert-ExistingPlanPath {
  param([string]$Value, [string]$Code)

  # The dump is committed, so the stored value is relative and forward slashed. plans/done/
  # is accepted because stage 16 archives the file and the row follows it there.
  $path = $Value.Replace('\', '/')
  if ($path -cnotmatch '^plans/(?:done/)?[^/]+$') {
    Stop-With 3 ("invalid --plan-path '$Value': it must be relative to the project root " +
      'and name a file directly under plans/ or plans/done/')
  }
  $base = Split-Path -Leaf $path
  # A plan file is always named <CODE>-<NNNNN>-<date>-<slug>.md, so its basename begins
  # with the code and a hyphen, and the schema's own instr(plan_path, code || '-') test
  # accepts exactly the same set. Nothing else is tolerated.
  if (-not $base.StartsWith($Code + '-', [StringComparison]::Ordinal)) {
    Stop-With 3 "invalid --plan-path '$Value': its file name must start with this row's code $Code followed by a hyphen"
  }
  $plansDir = Join-Path $script:Root 'plans'
  $present = (Test-Path -LiteralPath (Join-Path $plansDir $base) -PathType Leaf) -or
             (Test-Path -LiteralPath (Join-Path $plansDir "done/$base") -PathType Leaf)
  if (-not $present) {
    Stop-With 3 "invalid --plan-path '$Value': no such file under plans/ or plans/done/ in $($script:Root)"
  }
  return $path
}

$script:AssignStatement = @'
WITH payload AS (
  SELECT value AS v FROM json_each(readfile(:payload))
),
next_number AS (
  SELECT json_extract(v,'$.indicator') AS ind,
         (SELECT MAX(n) + 1 FROM (
            SELECT COALESCE((SELECT MAX(number) FROM work_item
                              WHERE indicator = json_extract(v,'$.indicator')), 0) AS n
            UNION ALL
            SELECT CAST(COALESCE(json_extract(v,'$.git_max'), 0) AS INTEGER) AS n)) AS num,
         v
    FROM payload
)
INSERT INTO work_item (indicator, number, title, state, owner_role, claiming_branch,
                       plan_path, committed_at, created_on, actor_host, actor_user)
SELECT ind, num,
       json_extract(v,'$.title'),
       'committed',
       json_extract(v,'$.role'),
       replace(json_extract(v,'$.branch'),    '{code}', ind || '-' || printf('%05d', num)),
       replace(json_extract(v,'$.plan_path'), '{code}', ind || '-' || printf('%05d', num)),
       strftime('%Y-%m-%dT%H:%M:%fZ','now'),
       strftime('%Y-%m-%d','now'),
       json_extract(v,'$.host'),
       json_extract(v,'$.user')
  FROM next_number;

INSERT INTO allocation_event (indicator, number, event, actor_role, actor_host, actor_user, detail)
SELECT indicator, number, 'assign', owner_role, actor_host, actor_user,
       'assigned at approval, db_max ' ||
       CAST(COALESCE(json_extract(readfile(:payload),'$[0].db_max'), 0) AS INTEGER)
  FROM work_item
 WHERE id = last_insert_rowid();

-- The stored text is proved against the code the row actually carries, never against
-- the candidate this process computed. The test is "code followed by a hyphen", not
-- "code": a bare instr() also matches a prefix sibling, so instr(x,'AVRIG-00005') is
-- satisfied by 'feat/AVRIG-000051-x' whereas instr(x,'AVRIG-00005-') is not.
-- A temporary CHECK constraint fails only its own statement, so this guard aborts the
-- transaction solely because '.bail on' is already in effect when it runs and the
-- COMMIT below is never reached. Do not move this below COMMIT and do not drop
-- '.bail on', or the row commits with the mismatched text and the guard silently
-- stops guarding.
CREATE TEMP TABLE ck_stored_code (
  ok INTEGER NOT NULL,
  CONSTRAINT ck_assign_stored_code CHECK (ok = 1)
);
INSERT INTO ck_stored_code (ok)
SELECT CASE WHEN instr(claiming_branch, code || '-') > 0
             AND instr(plan_path,      code || '-') > 0 THEN 1 ELSE 0 END
  FROM work_item
 WHERE id = (SELECT MAX(id) FROM work_item);
DROP TABLE ck_stored_code;
'@

function Invoke-Assign {
  Initialize-Project
  Initialize-Sqlite
  Initialize-Indicator

  $title = Get-OptValue 'title' ''
  if ([string]::IsNullOrWhiteSpace($title)) { Stop-With 3 'invalid --title: it must not be empty' }

  $role = Get-OptValue 'role' 'Architect'
  if ([string]::IsNullOrWhiteSpace($role)) { Stop-With 3 'invalid --role: it must not be empty' }

  $branchTemplate = Get-OptValue 'branch' ''
  if ([string]::IsNullOrWhiteSpace($branchTemplate)) { Stop-With 3 'missing --branch' }

  $planPathTemplate = Get-OptValue 'plan-path' ''
  if ([string]::IsNullOrWhiteSpace($planPathTemplate)) { Stop-With 3 'missing --plan-path' }

  $issueText = Get-OptValue 'issue' ''
  $issue = 0
  if ($issueText -ne '') {
    if ($issueText -cnotmatch '^[1-9][0-9]{0,8}$') {
      Stop-With 3 "invalid --issue '$issueText': it must be a positive integer"
    }
    $issue = [int]$issueText
  }

  # Self healing: a missing database is rebuilt from the dump, and a project with no
  # dump at all is initialised, because neither is a decision the caller should make.
  if (-not (Test-Path -LiteralPath $script:DbPath -PathType Leaf)) {
    if (Test-Path -LiteralPath $script:DumpPath -PathType Leaf) { Invoke-Import | Out-Null }
    else { Invoke-Init | Out-Null }
  }
  Initialize-Database | Out-Null

  $defaultBranch = Resolve-DefaultBranch
  $union = Get-GitUnion -DefaultBranch $defaultBranch
  foreach ($warning in $union.Warnings) { Write-Warn $warning }

  $dbMax = Get-DbMax
  $dumpMax = Get-DumpMax -DumpPath $script:DumpPath -Indicator $script:Indicator
  $remoteDumpMax = 0
  if ($defaultBranch -ne '' -and $union.HasGit) {
    $remote = Get-RemoteDumpMax -DefaultBranch $defaultBranch -Indicator $script:Indicator
    if ($remote.Warning -ne '') { Write-Warn $remote.Warning }
    $remoteDumpMax = $remote.Max
  }

  $candidate = Get-ProspectiveNumber -DbMax $dbMax -DumpMax $dumpMax -RemoteDumpMax $remoteDumpMax -Numbers $union.Numbers
  # Validation only: both functions return the template unsubstituted, and the statement
  # substitutes the number it actually writes.
  Assert-BranchInput -Template $branchTemplate -Number $candidate.Number | Out-Null
  Assert-PlanPathInput -Template $planPathTemplate -Number $candidate.Number | Out-Null

  $code = '{0}-{1:D5}' -f $script:Indicator, $candidate.Number
  $hostName = [Environment]::MachineName
  $userName = [Environment]::UserName
  # The statement derives its own number as MAX(db, git_max) + 1, so git_max has to be
  # the highest claim outside the database, not just the filename claim, or the statement
  # writes a number below a claim that git already carries.
  $gitMax = [Math]::Max($dumpMax, [Math]::Max($remoteDumpMax, $candidate.ClaimMax))

  if (Test-Flag 'dry-run') {
    $preview = [ordered]@{
      code    = $code
      number  = $candidate.Number
      state   = 'candidate'
      dry_run = $true
      db_max  = $dbMax
      dump_max = $dumpMax
      remote_dump_max = $remoteDumpMax
      claim_max = $candidate.ClaimMax
    }
    Write-Out (ConvertTo-Json -InputObject $preview -Compress)
    return 0
  }

  $payload = [ordered]@{
    indicator = $script:Indicator
    title     = $title
    branch    = $branchTemplate
    plan_path = $planPathTemplate
    role      = $role
    host      = $hostName
    user      = $userName
    git_max   = [int]$gitMax
    db_max    = [int]$dbMax
  }

  $body = $script:AssignStatement
  if ($issue -gt 0) {
    # The optional feature request number is written in the same transaction, after
    # the assignment's own statements, because the flag would otherwise be discarded.
    $payload['issue'] = $issue
    $body = $body + @'

UPDATE work_item
   SET issue_number = CAST(json_extract(readfile(:payload),'$[0].issue') AS INTEGER)
 WHERE id = (SELECT MAX(id) FROM work_item);
'@
  }

  $file = New-PayloadFile $payload
  try {
    $lines = @(
      '.bail on'
      '.timeout 5000'
      ".parameter set :payload '$file'"
      'PRAGMA busy_timeout = 5000;'
      'BEGIN IMMEDIATE;'
      ''
      $body
      ''
      'COMMIT;'
      "SELECT 'ROW|'||code||'|'||number||'|'||state||'|'||claiming_branch||'|'||plan_path FROM work_item WHERE id = (SELECT MAX(id) FROM work_item);"
    )
    $result = Invoke-Sqlite -Database $script:DbPath -Script $lines
  } finally {
    Remove-PayloadFile $file
  }

  if ($result.Exit -ne 0) {
    Stop-With (Resolve-SqliteExit $result) "assign failed: $($result.Text)"
  }

  # Exactly one stored row line proves a row was written, and the line carries the
  # branch and plan path as stored, so the JSON reports what the database holds rather
  # than what this process asked for. Under contention the stored number is higher than
  # the candidate, which is correct: the statement's number is the authoritative one.
  $rowLines = @($result.Lines | Where-Object { $_.StartsWith('ROW|') })
  if ($rowLines.Count -ne 1) {
    Stop-With 3 ("assign wrote no row: sqlite3 exited 0 but stdout carried $($rowLines.Count) " +
      'stored row line(s); the payload path is untrustworthy')
  }

  $rowMatch = [regex]::Match([string]$rowLines[0],
    '^ROW\|(?<code>[A-Z][A-Z0-9]{1,9}-\d{5})\|(?<number>\d+)\|(?<state>[a-z]+)\|(?<branch>[^|]*)\|(?<path>[^|]*)$')
  if (-not $rowMatch.Success) {
    Stop-With 3 "assign wrote a row but its result line could not be read: $($rowLines[0])"
  }

  $storedCode = $rowMatch.Groups['code'].Value
  $storedBranch = $rowMatch.Groups['branch'].Value
  $storedPath = $rowMatch.Groups['path'].Value
  if (-not $storedBranch.Contains("$storedCode-") -or -not $storedPath.Contains("$storedCode-")) {
    Stop-With 3 "assign stored a branch or plan path that does not carry $storedCode`: [$storedBranch] [$storedPath]"
  }

  $assigned = [ordered]@{
    code      = $storedCode
    number    = [int]$rowMatch.Groups['number'].Value
    state     = $rowMatch.Groups['state'].Value
    branch    = $storedBranch
    plan_path = $storedPath
    db_max    = $dbMax
    dump_max  = $dumpMax
    remote_dump_max = $remoteDumpMax
    claim_max = $candidate.ClaimMax
  }
  if ($issue -gt 0) { $assigned['issue'] = $issue }
  Write-Out (ConvertTo-Json -InputObject $assigned -Compress)
  return 0
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

$exitCode = 0
try {
  Parse-CliArgs -Argv $args
  switch ($script:Subcommand) {
    'init' { $exitCode = Invoke-Init }
    'import' { $exitCode = Invoke-Import }
    'export' { $exitCode = Invoke-Export }
    'assign' { $exitCode = Invoke-Assign }
    'void' { $exitCode = Invoke-Void }
    'update' { $exitCode = Invoke-Update }
    'status' { $exitCode = Invoke-Status }
    'verify' { $exitCode = Invoke-Verify }
    default { Stop-With 3 "unknown subcommand '$($script:Subcommand)'" }
  }
} catch {
  $exception = $_.Exception
  if ($exception -is [System.OperationCanceledException] -and $exception.Message.StartsWith('__plan_code_exit:')) {
    $exitCode = [int]($exception.Message.Substring('__plan_code_exit:'.Length))
  } else {
    [Console]::Error.WriteLine("error: $($exception.Message)")
    $exitCode = 3
  }
}
exit $exitCode
