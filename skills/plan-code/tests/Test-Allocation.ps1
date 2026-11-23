#Requires -Version 7.0
<#
  Test-Allocation.ps1

  Automated test suite for the plan-code allocator (shared/skills/plan-code/plan-code.ps1)
  and its schema (shared/skills/plan-code/schema/001-plan.sql), retargeted to the
  dump-backed design.

  Implements scenarios T01 to T21 of
  avrig-ai/plans/AVRIG-00004-2026-11-20-plan-code-sqlite-allocation.md,
  section "## Test Specification and Validation Scenarios".

  The suite tests the CONTRACT, never the implementation: eight subcommands
  (init, import, assign, void, status, verify, export, update), the exit code set
  (0 ok, 1 verification or drift, 2 contention, 3 invalid input or configuration,
  4 git failure), the {code} placeholder in --branch and --plan-path, and
  status --json emitting snake_case column names.

  What changed from the markdown-ledger design and how this suite follows it:

    - plans/PLAN-INDEX.md is gone. The durable archive is a deterministic plain
      text dump, plans/_plan.sql, written by export. There is no render, no
      marker block, and no markdown import.
    - import deletes plans/_plan.db and applies plans/_plan.sql with
      sqlite3 <db> ".read <dump>".
    - work_item has no ledger_cells column, ck_committed_branch is strict again,
      and the new tables deferred_defect and indicator_alias exist.
    - plans/PLAN-RULES.md carries the indicator declaration in its frontmatter.
    - verify checks three things: the dump matches what export would write, every
      git-union number is present in the database, and the rules document's
      indicator equals the database's.

  Fixture isolation: every fixture repository, dump, database and payload lives
  under $env:TEMP\opencode\plan-code\<pid>-<guid>, a root unique to this run so two
  runs started at the same time cannot delete each other's fixtures. -Scratch
  overrides it. Nothing in this file writes to the live avrig-ai checkout, its
  plans/PLAN-RULES.md, or plans/_plan.db.

  Deliberate choices, each reported to the reviewer:

    1. A fixture seeds its database by applying the shipped DDL, and where a
       durable archive is required it produces plans/_plan.sql with the tool's
       own export. A schema or export change therefore cannot pass unnoticed,
       and the dump is always in the one format verify compares against.
    2. T09 grades dump determinism by SHA-256: export twice, export of an
       imported dump, and export -> delete -> import -> export around a title
       carrying a single quote, a backslash, and a SQL injection attempt.
    3. T10(b) produces the "row in the dump that the database lacks" state by
       exporting a larger scratch database and copying its dump in, never by
       hand editing dump text. The case stays format agnostic.
    4. T03 part b runs against the OneDrive path only with -IncludeOneDrive. The
       default keeps every fixture under $env:TEMP as the runner contract requires.
    5. status --json is read through Get-StatusRows, which accepts a JSON array,
       a single object, or one object per line. The contract fixes the field names
       and one object per row, not the envelope, and T15 and T17 assert exact counts.
    6. T01 adds a direct proof that the shipped DDL applies on its own, so a hand
       rolled schema inside init cannot pass the case while 001-plan.sql is broken.
    7. T19 is the only case that reads the candidate tree instead of a fixture, because
       its subject is the migration's leftovers in that tree, and it loads the committed
       plans/_plan.sql into a scratch database so it still writes nothing.
    8. T20 grades the update subcommand, which is spec first. A missing subject is
       reported as BLOCKED with the observed refusal, never as a pass and never as a
       skip: BLOCKED fails the run, because an unexecuted case is not evidence.
    9. T21 grades the pointer check that decision 12 added after the live ledger failed
       it: every committed row has to name a file that is really there, and update
       --plan-path is the repair. A fixture row is seeded with the file it names, since
       a committed row pointing at nothing is the very drift the case is about.
#>

[CmdletBinding()]
param(
  [string]$Project = 'D:\Cloud\OneDrive\AI\Agentic\avrig-ai',

  # Evidence folder. Empty means "print only, write nothing outside the scratch root".
  [string]$Out = '',

  # Accepts -Case T03 or -Case T01,T02 or -Case T01 -Case T02.
  [string[]]$Case = @('T01','T02','T03','T04','T05','T06','T07','T08','T09','T10',
                      'T11','T12','T13','T14','T15','T16','T17','T18','T19','T20','T21'),

  # Candidate tag under test. Empty means a working tree run, which is not evidence.
  [string]$Tag = '',

  # Scratch root. Empty means a directory unique to this process, so two runs started at
  # the same time cannot delete each other's fixtures.
  [string]$Scratch = '',

  # Leave the scratch tree in place for inspection.
  [switch]$Keep,

  # Also run T03 part b against a synced OneDrive path. Off by default.
  [switch]$IncludeOneDrive
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false

# ---------------------------------------------------------------------------
# Constants, exactly as the harness contract fixes them.
# ---------------------------------------------------------------------------

$TOOL = 'D:\Cloud\OneDrive\AI\Agentic'
$PC   = Join-Path $TOOL 'shared\skills\plan-code\plan-code.ps1'
$DDL  = Join-Path $TOOL 'shared\skills\plan-code\schema\001-plan.sql'
$PW   = Join-Path $PSHOME 'pwsh.exe'
$SQL  = 'D:\miniconda3\envs\kb\Library\bin\sqlite3.exe'
$TMP  = if ($Scratch) {
  $Scratch
} else {
  # Per process, so a second run cannot share a fixture path. The PID alone would collide
  # across a long lived session, so a short GUID rides along. The variable is not named
  # $tag, because PowerShell variable names are case insensitive and that is -Tag.
  $runSuffix = ([guid]::NewGuid().ToString('N')).Substring(0, 8)
  Join-Path $env:TEMP (Join-Path 'opencode\plan-code' ("$PID-$runSuffix"))
}
$WT   = $Project

if (-not (Test-Path -LiteralPath $SQL)) {
  $cmd = Get-Command sqlite3 -ErrorAction SilentlyContinue
  if ($cmd) { $SQL = $cmd.Source }
}

$script:Total   = 0
$script:Passed  = 0
$script:Blocked = $null
$script:CaseLog = [System.Collections.Generic.List[string]]::new()

function Add-Log([string]$Line) {
  if ($null -eq $script:CaseLog) { $script:CaseLog = [System.Collections.Generic.List[string]]::new() }
  $script:CaseLog.Add($Line)
  Write-Verbose $Line
}

function Invoke-Pc {
  param([string]$Proj, [string[]]$Arg)
  Add-Log ('PC> pwsh -NoProfile -File plan-code.ps1 ' + ($Arg -join ' ') + ' --project ' + $Proj)
  $o = & $PW -NoProfile -File $PC @Arg --project $Proj 2>&1
  $code = $LASTEXITCODE
  $text = (@($o) -join "`n")
  Add-Log ("PC< exit=$code" + $(if ($text.Trim()) { "`n$text" } else { '' }))
  [pscustomobject]@{ Exit = $code; Out = $text }
}

function Assert-Equal($Expected, $Actual, [string]$What) {
  $script:Total++
  if ("$Expected" -cne "$Actual") {
    throw ("$What : expected [" + "$Expected" + "] got [" + "$Actual" + "]")
  }
  $script:Passed++
}

function Assert-Match([string]$Text, [string]$Pattern, [string]$What) {
  $script:Total++
  if ($Text -notmatch $Pattern) { throw "$What : no match for /$Pattern/ in [$Text]" }
  $script:Passed++
}

function Assert-True($Condition, [string]$What) {
  $script:Total++
  if (-not $Condition) { throw "$What : condition is false" }
  $script:Passed++
}

# A case whose subject does not exist yet is BLOCKED rather than failed or skipped.
# The reason travels to the result line, and the rollup counts it as not passing.
function Set-Blocked([string]$Reason) {
  $script:Blocked = $Reason
  Write-Verbose "BLOCKED: $Reason"
}

# The ledger_status vocabulary, written once because T02 and T19 both grade it.
$script:StatusVocab = @('draft','under-review','awaiting-approval','approved','in-progress',
                        'testing','passed','release-version-decided','merged','deployed',
                        'released','abandoned')

function Get-Code([string]$OutText) {
  $m = [regex]::Match($OutText, '"code"\s*:\s*"(?<c>[A-Z][A-Z0-9]{1,9}-\d{5})"')
  if (-not $m.Success) { throw "no code in output: $OutText" }
  $m.Groups['c'].Value
}

function Get-StatusRows([string]$JsonText) {
  $t = "$JsonText".Trim()
  if (-not $t) { return @() }
  $v = $null
  try { $v = $t | ConvertFrom-Json } catch {
    $lines = @($t -split "\r?\n" | Where-Object { $_.Trim() })
    $v = @($lines | ForEach-Object { $_ | ConvertFrom-Json })
  }
  if ($null -eq $v) { return @() }
  return @($v)
}

function Get-Sha256([string]$Path) {
  (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
}

function Assert-SameBytes([string]$A, [string]$B, [string]$What) {
  $script:Total++
  $ha = Get-Sha256 $A
  $hb = Get-Sha256 $B
  if ($ha -cne $hb) { throw "$What : $A [$ha] differs from $B [$hb]" }
  $script:Passed++
}

function Assert-NoBom([string]$Path, [string]$What) {
  $script:Total++
  $b = [IO.File]::ReadAllBytes($Path)
  if ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF) {
    throw "$What : $Path starts with a UTF-8 byte order mark"
  }
  $script:Passed++
}

function Invoke-Git {
  param([string]$Path, [string[]]$Arg)
  $o = & git -C $Path @Arg 2>&1
  [pscustomobject]@{ Exit = $LASTEXITCODE; Out = (@($o) -join "`n") }
}

function Assert-Git {
  param([string]$Path, [string[]]$Arg, [string]$What)
  $r = Invoke-Git $Path $Arg
  if ($r.Exit -ne 0) { throw "$What : git $($Arg -join ' ') exited $($r.Exit) : $($r.Out)" }
  return $r
}

function Invoke-Sql {
  param([string]$Db, [string]$Query)
  $o = & $SQL -noheader $Db $Query 2>&1
  $code = $LASTEXITCODE
  Add-Log ("SQL> $Query" + "`n" + "SQL< exit=$code" + "`n" + ((@($o) -join "`n")))
  [pscustomobject]@{ Exit = $code; Out = ((@($o) -join "`n").Trim()) }
}

# Start-Process joins an -ArgumentList array with spaces and adds no quoting of its
# own, so a value containing a space arrives as two arguments unless it is quoted here.
function Format-ProcessArg([string]$Value) {
  if ($Value -eq '') { return '""' }
  if ($Value -match '[\s"]') { return '"' + ($Value -replace '"', '\"') + '"' }
  return $Value
}

# ---------------------------------------------------------------------------
# Fixture builder. A throwaway repository whose durable archive is plans/_plan.sql
# and whose indicator declaration is plans/PLAN-RULES.md, seeded from the shipped
# DDL so a schema change cannot pass unnoticed. Nothing here touches the live
# checkout, and the database file is ignored exactly as the design says.
# ---------------------------------------------------------------------------

function Write-RulesDoc([string]$Path, [string]$Indicator, [string]$Prose = '') {
  $md = @(
    '---',
    'title: Plan Rules',
    "project_indicator: $Indicator",
    '---',
    '# Plan Rules',
    '',
    'Allocation rules and status vocabulary for this project.',
    ''
  )
  if ($Prose) { $md += @($Prose, '') }
  [IO.File]::WriteAllText($Path, ($md -join "`n"), [Text.UTF8Encoding]::new($false))
}

# The plan file a fixture row names. A committed row has to point at a file that is
# really there: verify reports drift when the pointer does not resolve, so the fixture
# materialises the file the row names rather than inventing a plausible path. Row 1
# lives in plans/done/ so that the archived shape is exercised too.
function Get-FixturePlanPath([int]$Number) {
  if ($Number -eq 1) { return 'plans/done/AVRIG-00001-2026-11-20-fixture-one.md' }
  return ('plans/AVRIG-{0:D5}-2026-11-20-fixture-{0}.md' -f $Number)
}

function New-PlanFile([string]$Repo, [string]$RelPath) {
  $full = Join-Path $Repo ($RelPath.Replace('/', '\'))
  New-Item -ItemType Directory -Force (Split-Path -Parent $full) | Out-Null
  [IO.File]::WriteAllText($full, "# fixture plan`n", [Text.UTF8Encoding]::new($false))
  return $RelPath
}

# Applies the shipped DDL and inserts rows directly, so the fixture seed is built
# from the real schema rather than a hand rolled table.
function New-SeedDb([string]$Repo, [int]$Rows) {
  $db = Join-Path $Repo 'plans\_plan.db'
  Remove-Item -Force $db, "$db-wal", "$db-shm" -ErrorAction SilentlyContinue
  $o = (Get-Content -Raw -LiteralPath $DDL | & $SQL $db 2>&1)
  if ($LASTEXITCODE -ne 0) { throw "the shipped DDL did not apply to the fixture : $(@($o) -join ' ')" }

  $sqlText = "INSERT INTO project (indicator,project_key) VALUES ('AVRIG','fixture');`n"
  for ($n = 1; $n -le $Rows; $n++) {
    $code = 'AVRIG-{0:D5}' -f $n
    $pp = Get-FixturePlanPath $n
    $sqlText += "INSERT INTO work_item (indicator,number,title,created_on,state,owner_role,actor_host,actor_user,claiming_branch,plan_path,assigned_at,committed_at) " +
            "VALUES ('AVRIG',$n,'Fixture $n','2026-11-20','committed','Architect','h','u','feat/$code-fixture','$pp','2026-11-20T00:00:00.000Z','2026-11-20T00:00:00.000Z');`n"
    $sqlText += "INSERT INTO allocation_event (indicator,number,event,actor_role,actor_host,actor_user,detail) " +
            "VALUES ('AVRIG',$n,'assign','Architect','h','u','seed');`n"
  }
  $out = ($sqlText | & $SQL -bail $db 2>&1) -join "`n"
  if ($LASTEXITCODE -ne 0) { throw "the fixture seed rows did not insert : $out" }
}

function Invoke-Export([string]$Proj, [switch]$Check) {
  if ($Check) { Invoke-Pc $Proj @('export','--check') } else { Invoke-Pc $Proj @('export') }
}

function New-FixtureRepo {
  param(
    [string]$Path,
    [int]$LedgerMax = 3,
    [switch]$SeedDb,
    [switch]$ExportDump,
    [string]$Prose = ''
  )
  Remove-Item -Recurse -Force $Path -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force (Join-Path $Path 'plans\done') | Out-Null
  $origin = "$Path-origin.git"
  Remove-Item -Recurse -Force $origin -ErrorAction SilentlyContinue
  & git init -q --bare -b main $origin
  if ($LASTEXITCODE -ne 0) { throw "New-FixtureRepo: git init --bare failed for $origin" }
  & git -C $Path init -q -b main
  if ($LASTEXITCODE -ne 0) { throw "New-FixtureRepo: git init failed for $Path" }

  # byte faithful fixtures: no line ending normalisation, so a diff is a diff
  foreach ($kv in @(@('user.email','t@example.invalid'),
                    @('user.name','tester'),
                    @('core.autocrlf','false'),
                    @('core.safecrlf','false'),
                    @('commit.gpgsign','false'))) {
    Assert-Git $Path @('config', $kv[0], $kv[1]) "fixture config $($kv[0])" | Out-Null
  }
  Assert-Git $Path @('remote','add','origin',$origin) 'fixture remote' | Out-Null

  # The indicator declaration site is the rules document, not a markdown ledger.
  Write-RulesDoc (Join-Path $Path 'plans\PLAN-RULES.md') 'AVRIG' $Prose

  # The database is ignored, the dump is tracked, exactly as the design says.
  [IO.File]::WriteAllText((Join-Path $Path '.gitignore'), "plans/_plan.db*`n", [Text.UTF8Encoding]::new($false))

  # Coded plan files feed the git union through the anchored filename rule, and each
  # seeded row names the file it gets here, because a committed row pointing at nothing
  # is drift that verify now reports.
  for ($n = 1; $n -le $LedgerMax; $n++) {
    New-PlanFile $Path (Get-FixturePlanPath $n) | Out-Null
  }
  [IO.File]::WriteAllText((Join-Path $Path 'plans\2026-11-20-uncoded-draft.md'), "# draft`n",
                          [Text.UTF8Encoding]::new($false))

  if ($SeedDb -or $ExportDump) { New-SeedDb $Path $LedgerMax }

  Assert-Git $Path @('add','-A') 'fixture add' | Out-Null
  Assert-Git $Path @('commit','-q','-m','fixture') 'fixture commit' | Out-Null
  Assert-Git $Path @('push','-q','-u','origin','main') 'fixture push' | Out-Null

  # a real clone carries refs/remotes/origin/HEAD, and the default branch contract
  # resolves through it; without it the fixture is not the shape of a clone
  Assert-Git $Path @('remote','set-head','origin','main') 'fixture origin HEAD' | Out-Null

  if ($LedgerMax -ge 1) {
    $b = ('feat/AVRIG-{0:D5}-fixture-branch' -f $LedgerMax)
    Assert-Git $Path @('branch',$b) 'fixture branch' | Out-Null
    Assert-Git $Path @('push','-q','origin',$b) 'fixture branch push' | Out-Null
  }

  # The durable archive is produced by the tool's own export so the format is the
  # one verify compares against. A broken export fails here rather than silently
  # seeding a dump no verify would ever accept.
  if ($ExportDump) {
    $e = Invoke-Export $Path
    if ($e.Exit -ne 0) { throw "the fixture export failed : exit $($e.Exit) : $($e.Out)" }
    if (-not (Test-Path -LiteralPath (Join-Path $Path 'plans\_plan.sql'))) {
      throw 'the fixture export produced no plans/_plan.sql'
    }
    Assert-Git $Path @('add','-A') 'dump add' | Out-Null
    Assert-Git $Path @('commit','-q','-m','dump') 'dump commit' | Out-Null
    Assert-Git $Path @('push','-q','origin','main') 'dump push' | Out-Null
  }
}

# A legal committed row helper for direct SQL probes in T02.
function New-ProbeRow([int]$Number, [hashtable]$Over = @{}) {
  $f = [ordered]@{
    Indicator = 'AVRIG'; Title = "probe $Number"; State = 'committed'; Role = 'Architect'
    Branch    = ('feat/AVRIG-{0:D5}-probe' -f $Number)
    PlanPath  = ('plans/AVRIG-{0:D5}-2026-11-20-probe.md' -f $Number)
    CommittedAt = '2026-11-20T00:00:00.000Z'; CreatedOn = '2026-11-20'; Host = 'h'; User = 'u'
  }
  if ($Over) { foreach ($k in $Over.Keys) { $f[$k] = $Over[$k] } }
  $vals = @($f.Indicator, $Number, $f.Title, $f.State, $f.Role, $f.Branch, $f.PlanPath,
            $f.CommittedAt, $f.CreatedOn, $f.Host, $f.User) |
          ForEach-Object {
            if ($null -eq $_) { 'NULL' }
            elseif ($_ -is [int]) { "$_" }
            else { "'" + ($_ -replace "'","''") + "'" }
          }
  'INSERT INTO work_item (indicator,number,title,state,owner_role,claiming_branch,plan_path,' +
  'committed_at,created_on,actor_host,actor_user) VALUES (' + ($vals -join ',') + ');'
}

# ---------------------------------------------------------------------------
# T01 Schema creation and integrity
# ---------------------------------------------------------------------------

function Invoke-Case-T01 {
  $repo = Join-Path $TMP 't01'
  New-FixtureRepo $repo 0
  $db = Join-Path $repo 'plans\_plan.db'

  Assert-True (-not (Test-Path -LiteralPath $db)) 'the database file is absent before init'
  Assert-Equal 0 (Invoke-Pc $repo @('init','--indicator','AVRIG')).Exit 'init exit'
  Assert-Match ([IO.File]::ReadAllText($DDL)) 'PRAGMA user_version\s*=\s*1' 'the shipped DDL declares version 1'
  Assert-Equal 1 (& $SQL -noheader $db 'PRAGMA user_version;') 'user_version'
  Assert-Equal 'ok' (& $SQL -noheader $db 'PRAGMA integrity_check;') 'integrity_check'
  Assert-Equal 'wal' (& $SQL -noheader $db 'PRAGMA journal_mode;') 'journal_mode'

  $t = (& $SQL -noheader $db "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;") -join ','
  Assert-Equal 'allocation_event,deferred_defect,indicator_alias,project,work_item' $t 'tables'

  $i = (& $SQL -noheader $db "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name;") -join ','
  Assert-Equal 'ix_work_item_state' $i 'indexes'
  Assert-Equal 'state' (& $SQL -noheader $db "SELECT name FROM pragma_index_info('ix_work_item_state');") 'the one index is on state, not on an expiry column'

  $g = (& $SQL -noheader $db "SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name;") -join ','
  Assert-Equal 'tr_allocation_event_no_delete,tr_allocation_event_no_update,tr_work_item_no_delete,tr_work_item_no_rekey' $g 'triggers'

  Assert-Equal 'AVRIG' (& $SQL -noheader $db 'SELECT indicator FROM project;') 'project row'
  Assert-Equal 2 ([int](& $SQL -noheader $db "SELECT COUNT(*) FROM pragma_table_info('work_item') WHERE name IN ('created_on','repos');")) 'render source columns exist as data'
  Assert-Equal 0 ([int](& $SQL -noheader $db "SELECT COUNT(*) FROM pragma_table_info('work_item') WHERE name='ledger_cells';")) 'ledger_cells is gone with the markdown layer'
  Assert-Equal 0 ([int](& $SQL -noheader $db "SELECT COUNT(*) FROM pragma_table_info('work_item') WHERE name IN ('lease_token','lease_expires_at','reserved_at');")) 'no lease column survived the design change'

  # the generated code is omitted by table_info and flagged hidden by table_xinfo,
  # which is exactly what a column list driven dumper has to rely on
  Assert-Equal 0 ([int](& $SQL -noheader $db "SELECT COUNT(*) FROM pragma_table_info('work_item') WHERE name='code';")) 'the generated code is not a plain table_info column'
  Assert-Equal 3 (& $SQL -noheader $db "SELECT hidden FROM pragma_table_xinfo('work_item') WHERE name='code';") 'the generated code is hidden in table_xinfo'

  $dd = (& $SQL -noheader $db "SELECT name FROM pragma_table_info('deferred_defect') ORDER BY cid;") -join ','
  Assert-Equal 'id,found_during,defect,evidence,at' $dd 'deferred_defect columns'
  $ia = (& $SQL -noheader $db "SELECT name FROM pragma_table_info('indicator_alias') ORDER BY cid;") -join ','
  Assert-Equal 'old_code,new_code,migrated_on' $ia 'indicator_alias columns'

  # Added: the shipped DDL must stand on its own, so init cannot hide a broken asset.
  $ddlDb = Join-Path $repo 'ddl-probe.db'
  Remove-Item -Force $ddlDb -ErrorAction SilentlyContinue
  $o = (Get-Content -Raw -LiteralPath $DDL | & $SQL $ddlDb 2>&1)
  if ($LASTEXITCODE -ne 0) { throw "the shipped DDL did not apply on its own : $(@($o) -join ' ')" }
  Assert-Equal 1 (& $SQL -noheader $ddlDb 'PRAGMA user_version;') 'the DDL sets user_version on its own'
  Assert-Equal 'ok' (& $SQL -noheader $ddlDb 'PRAGMA integrity_check;') 'the DDL builds an integrable database on its own'
  $dt = (& $SQL -noheader $ddlDb "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;") -join ','
  Assert-Equal 'allocation_event,deferred_defect,indicator_alias,project,work_item' $dt 'the DDL creates all five tables on its own'
  $dg = (& $SQL -noheader $ddlDb "SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name;") -join ','
  Assert-Equal 'tr_allocation_event_no_delete,tr_allocation_event_no_update,tr_work_item_no_delete,tr_work_item_no_rekey' $dg 'the DDL creates all four triggers on its own'
}

# ---------------------------------------------------------------------------
# T02 Constraint proof, table driven
# ---------------------------------------------------------------------------

function Invoke-Case-T02 {
  $repo = Join-Path $TMP 't02'
  New-FixtureRepo $repo 0
  Assert-Equal 0 (Invoke-Pc $repo @('init','--indicator','AVRIG')).Exit 'init exit'
  $db = Join-Path $repo 'plans\_plan.db'

  # init registers the indicator, so the project row is asserted rather than inserted.
  Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM project;') 'init registered exactly one project row'

  $seed = @"
INSERT INTO work_item (indicator,number,title,state,owner_role,claiming_branch,plan_path,committed_at,created_on,actor_host,actor_user)
VALUES ('AVRIG',4,'baseline','committed','Architect','feat/AVRIG-00004-baseline',
        'plans/AVRIG-00004-2026-11-20-baseline.md','2026-11-20T00:00:00.000Z','2026-11-20','h','u');
INSERT INTO allocation_event (indicator,number,event,actor_role,actor_host,actor_user,detail)
VALUES ('AVRIG',4,'assign','Architect','h','u','baseline row');
INSERT INTO indicator_alias (old_code,new_code,migrated_on) VALUES ('OLD','NEW','2026-11-20');
"@
  $seedOut = (& $SQL -bail $db $seed 2>&1) -join "`n"
  Assert-Equal 0 $LASTEXITCODE "baseline seed : $seedOut"
  Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;') 'baseline row seeded'
  Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;') 'baseline event seeded, so the append-only triggers have a row to fire on'
  Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM indicator_alias;') 'alias row seeded, so the duplicate can be probed'

  $rows = @(
    @{ Id='02a';  Number=4;      Over=@{} }
    @{ Id='02c';  Number=5;      Over=@{ State='pending' } }
    @{ Id='02c2'; Number=6;      Over=@{ State='reserved' } }
    @{ Id='02d';  Number=7;      Over=@{ Title='' } }
    @{ Id='02e';  Number=8;      Over=@{ Title='   ' } }
    @{ Id='02f';  Number=0;      Over=@{} }
    @{ Id='02g';  Number=100000; Over=@{} }
    @{ Id='02n';  Number=9;      Over=@{ Branch=$null } }
    @{ Id='02o';  Number=10;     Over=@{ CommittedAt=$null } }
    @{ Id='02p';  Number=11;     Over=@{ State='voided'; Branch=$null; CommittedAt=$null } }
    @{ Id='02z1'; Number=12;     Over=@{ Role='' } }
    @{ Id='02z3'; Number=13;     Over=@{ Host='' } }
    @{ Id='02z4'; Number=14;     Over=@{ User='  ' } }
    @{ Id='02aa'; Number=15;     Over=@{ Branch='feat/AVRIG-00009-other' } }
    @{ Id='02ab'; Number=16;     Over=@{ CreatedOn='20-11-2026' } }
    # The tightened ck_branch_carries_code: the code must be followed by a hyphen, so
    # the prefix sibling 'AVRIG-000051-x' no longer satisfies the check for number 5.
    # The old expression, instr(branch, 'AVRIG-00005'), accepted it, which is why it changed.
    @{ Id='02ac'; Number=5;      Over=@{ Branch='feat/AVRIG-000051-x' } }
    @{ Id='02m';  Number=1;      Over=@{ Indicator='WEB'; Branch='feat/WEB-00001-fk'
                                         PlanPath='plans/WEB-00001-2026-11-20-fk.md' }
                                  Extra=@('-cmd','PRAGMA foreign_keys=ON;') }
  )

  $statements = @(
    @{ Id='02h'; Sql="INSERT INTO project (indicator,project_key) VALUES ('avrig','k-h');" }
    @{ Id='02i'; Sql="INSERT INTO project (indicator,project_key) VALUES ('AVR IG','k-i');" }
    @{ Id='02j'; Sql="INSERT INTO project (indicator,project_key) VALUES ('AVRIG-','k-j');" }
    @{ Id='02k'; Sql="INSERT INTO project (indicator,project_key) VALUES ('AVRIGAVRIGAV','k-k');" }
    @{ Id='02l'; Sql="INSERT INTO project (indicator,project_key) VALUES ('A','k-l');" }
    @{ Id='02q'; Sql='UPDATE project SET frozen = 2;' }
    @{ Id='02r'; Sql="INSERT INTO allocation_event (indicator,number,event,actor_role,actor_host,actor_user) VALUES ('AVRIG',4,'reserve','Architect','h','u');" }
    @{ Id='02s'; Sql="UPDATE allocation_event SET detail = 'x';" }
    @{ Id='02t'; Sql='DELETE FROM allocation_event;' }
    @{ Id='02u'; Sql='DELETE FROM work_item WHERE number = 4;' }
    @{ Id='02v'; Sql='UPDATE work_item SET number = 5 WHERE number = 4;' }
    @{ Id='02w'; Sql="UPDATE work_item SET indicator = 'AVRIH' WHERE number = 4;" }
    @{ Id='02df1'; Sql="INSERT INTO deferred_defect (found_during,defect) VALUES ('','x');" }
    @{ Id='02df2'; Sql="INSERT INTO deferred_defect (found_during,defect) VALUES ('AVRIG-00001','   ');" }
    @{ Id='02ia'; Serial=$true; Sql="INSERT INTO indicator_alias (old_code,new_code,migrated_on) VALUES ('OLD','OTHER','2026-11-20');" }
  )

  # (b) both unique constraints are structural: code is generated from (indicator, number)
  Assert-Equal 2 ([int](& $SQL -noheader $db "SELECT (sql LIKE '%uq_work_item_number%') + (sql LIKE '%uq_work_item_code%') FROM sqlite_master WHERE type='table' AND name='work_item';")) 'both unique constraints present in the DDL'

  $probes = 0
  foreach ($c in $rows) {
    $probes++
    $sqlText = New-ProbeRow ([int]$c.Number) $c.Over
    $extra = @($c.Extra | Where-Object { $_ })
    $sa = @('-bail') + $extra + @($db, $sqlText)
    Add-Log ("PROBE $($c.Id) : " + $sqlText)
    $o = (& $SQL @sa 2>&1) -join "`n"
    $code = $LASTEXITCODE
    $text = if ($c.Id -eq '02a') { 'UNIQUE constraint failed' }
            elseif ($c.Id -eq '02m') { 'FOREIGN KEY constraint failed' }
            elseif ($c.Id -eq '02n') { 'ck_committed_branch' }
            elseif ($c.Id -eq '02p') { 'ck_voided_reason' }
            else { 'CHECK constraint failed' }
    Assert-Equal 19 $code "$($c.Id) sqlite3 exit (SQLITE_CONSTRAINT)"
    Assert-Match $o ([regex]::Escape($text)) "$($c.Id) refusal text"
  }

  foreach ($c in $statements) {
    $probes++
    Add-Log ("PROBE $($c.Id) : " + $c.Sql)
    $o = (& $SQL -bail $db $c.Sql 2>&1) -join "`n"
    $code = $LASTEXITCODE
    $text = if ($c.Id -in @('02s','02t')) { 'allocation_event is append-only' }
            elseif ($c.Id -eq '02u') { 'work_item rows are permanent' }
            elseif ($c.Id -in @('02v','02w')) { 'indicator and number are immutable' }
            elseif ($c.Id -eq '02df1') { 'found_during' }
            elseif ($c.Id -eq '02df2') { 'defect' }
            elseif ($c.Id -eq '02ia') { 'UNIQUE constraint failed: indicator_alias.old_code' }
            else { 'CHECK constraint failed' }
    Assert-Equal 19 $code "$($c.Id) sqlite3 exit (SQLITE_CONSTRAINT)"
    Assert-Match $o ([regex]::Escape($text)) "$($c.Id) refusal text"
  }

  # The other half of a constraint proof: what must still be accepted. A check that
  # refuses everything would pass every probe above, so the accept side is graded too.
  $accepts = @(
    @{ Id='02ad'; Number=5; Over=@{ Branch='feat/AVRIG-00005-x' } }
    @{ Id='02ae'; Sql="INSERT INTO work_item (indicator,number,title,state,owner_role,claiming_branch,plan_path,voided_reason,actor_host,actor_user) VALUES ('AVRIG',6,'null branch','voided','Architect',NULL,NULL,'probe: voided rows may carry no branch','h','u');" }
    @{ Id='02af'; Sql="INSERT INTO allocation_event (indicator,number,event,actor_role,actor_host,actor_user,detail) VALUES ('AVRIG',4,'update','Architect','h','u','ledger_status');" }
  )
  foreach ($c in $accepts) {
    $probes++
    $sqlText = if ($c.ContainsKey('Over')) { New-ProbeRow ([int]$c.Number) $c.Over } else { $c.Sql }
    Add-Log ("ACCEPT $($c.Id) : " + $sqlText)
    $o = (& $SQL -bail $db $sqlText 2>&1) -join "`n"
    Assert-Equal 0 $LASTEXITCODE "$($c.Id) is accepted : $o"
  }

  $expectedProbes = $rows.Count + $statements.Count + $accepts.Count
  Assert-Equal $expectedProbes $probes 'every refusal probe ran'
  Assert-True ($expectedProbes -ge 30) 'the probe set still covers every constraint class'
  Assert-Equal 3 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;') 'the baseline row and the two accepted probes survive, and no refused probe landed'
  Assert-Equal 2 (& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;') 'the baseline event and the accepted update event survive'
  Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM indicator_alias;') 'only the seeded alias survives'
  Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) FROM deferred_defect;') 'no invalid defect row landed'
  Assert-Equal 0 (& $SQL -noheader $db "SELECT COUNT(*) FROM work_item WHERE state NOT IN ('committed','voided');") 'no retired state value reached a row'
  Assert-Equal 0 (& $SQL -noheader $db "SELECT COUNT(*) FROM project WHERE indicator <> 'AVRIG';") 'no invalid indicator reached the registry'

  # the allocation_event vocabulary gained 'update' and kept 'reserve' out
  Assert-Equal 1 (& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='update';") 'event=update is accepted by the vocabulary'
  Assert-Equal 0 (& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='reserve';") 'event=reserve is still refused'

  # the tightened check holds for every stored row, not only for the probes: the code
  # has to be followed by a hyphen, which a prefix sibling would fail
  Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item WHERE claiming_branch IS NOT NULL AND instr(claiming_branch, code || ''-'') = 0;') 'every stored branch carries its own code as a full token'
  Assert-Equal 'ok' (& $SQL -noheader $db 'PRAGMA integrity_check;') 'integrity after refusals'
}

# ---------------------------------------------------------------------------
# T03 Twenty way concurrency, including the {code} placeholder under a race
# ---------------------------------------------------------------------------

function Start-RaceAssign([string]$Repo, [int]$I, [string]$OutDir) {
  $a = @('-NoProfile','-File',$PC,'assign','--title',"concurrent $I",'--role','Architect',
         '--branch',"feat/{code}-race-$I",'--plan-path',"plans/{code}-2026-11-20-race-$I.md",
         '--project',$Repo)
  $line = (@($a | ForEach-Object { Format-ProcessArg $_ }) -join ' ')
  Start-Process -FilePath $PW -ArgumentList $line -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $OutDir "$I.out") `
    -RedirectStandardError  (Join-Path $OutDir "$I.err")
}

function Invoke-Race([string]$Repo, [string]$Label) {
  New-FixtureRepo $Repo 3 -SeedDb
  $db  = Join-Path $Repo 'plans\_plan.db'
  $out = Join-Path $Repo 'race-out'
  New-Item -ItemType Directory -Force $out | Out-Null

  # twenty records prepared before launch so process start jitter does not serialise
  # the writers by accident
  $procs = @()
  for ($i = 1; $i -le 20; $i++) {
    $procs += [pscustomobject]@{ I = $i; Proc = (Start-RaceAssign $Repo $i $out); Retried = $false }
  }
  foreach ($p in $procs) { $p.Proc.WaitForExit(); $p.Proc.WaitForExit() }   # second call flushes the streams

  # documented retry: exit 2 means nothing was written, so re-running is safe
  $retries = 0
  foreach ($p in $procs) {
    if ($p.Proc.ExitCode -eq 2) {
      $retries++
      $p.Retried = $true
      $again = Start-RaceAssign $Repo $p.I $out
      $again.WaitForExit(); $again.WaitForExit()
      $p.Proc = $again
    }
  }
  Add-Log "$Label retries=$retries"

  # One authoritative verdict per failure class, rather than a throw on the first
  # unexpected exit that hides how the other writers fared.
  $bad = @($procs | Where-Object { $_.Proc.ExitCode -ne 0 })
  if ($bad.Count -gt 0) {
    $classes = [ordered]@{}
    foreach ($p in $bad) {
      $errText = (Get-Content (Join-Path $out "$($p.I).err") -Raw -ErrorAction SilentlyContinue)
      $key = "$($p.Proc.ExitCode)"
      if ($errText -match 'ck_branch_carries_code') { $key += ' ck_branch_carries_code' }
      elseif ($errText -match 'UNIQUE constraint failed') { $key += ' UNIQUE' }
      elseif ($errText -match 'database is locked') { $key += ' database is locked' }
      elseif ($errText -match 'constraint failed') { $key += ' other constraint' }
      if (-not $classes.Contains($key)) { $classes[$key] = 0 }
      $classes[$key]++
    }
    $summary = (@($classes.Keys | ForEach-Object { "$_ x$($classes[$_])" }) -join '; ')
    $first = $bad[0]
    $firstErr = ((Get-Content (Join-Path $out "$($first.I).err") -Raw -ErrorAction SilentlyContinue) -replace '\s+', ' ').Trim()
    throw ("$Label : $($bad.Count) of $($procs.Count) writers did not succeed after the documented retry " +
           "[$summary]; writer $($first.I) said: $firstErr")
  }

  $stderr = ((Get-ChildItem $out -Filter '*.err' | ForEach-Object { Get-Content $_.FullName -Raw }) -join "`n")
  Assert-True (-not ($stderr -match 'Exception|NativeCommandError|malformed JSON')) "$Label : no exception on stderr"
  if ($stderr -match 'SQLITE_BUSY') { Add-Log "$Label : SQLITE_BUSY printed on stderr, retries=$retries" }

  $codes = @()
  for ($i = 1; $i -le 20; $i++) {
    $txt = Get-Content (Join-Path $out "$i.out") -Raw -ErrorAction SilentlyContinue
    $m = [regex]::Match("$txt", '"code"\s*:\s*"(?<c>[A-Z][A-Z0-9]{1,9}-\d{5})"')
    if ($m.Success) { $codes += $m.Groups['c'].Value }
  }
  $distinct = @($codes | Sort-Object -Unique)
  $want = @(4..23 | ForEach-Object { 'AVRIG-{0:D5}' -f $_ })

  Assert-Equal 20 $distinct.Count "$Label distinct codes"
  Assert-Equal 0 (@(Compare-Object $distinct $want)).Count "$Label set equals 00004..00023"
  Assert-Equal 23 (& $SQL -noheader $db "SELECT COUNT(*) FROM work_item WHERE state='committed';") "$Label committed rows (three seeded plus twenty assigned)"
  Assert-Equal 23 (& $SQL -noheader $db 'SELECT COUNT(DISTINCT code) FROM work_item;') "$Label distinct codes in db"
  Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item WHERE instr(claiming_branch, code) = 0;') "$Label every row carries its own code in its branch"
  Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item WHERE instr(plan_path, code) = 0;') "$Label every row carries its own code in its plan path"
  Assert-Equal 23 (& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='assign';") "$Label one assign event per row"
  Assert-Equal '4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23' `
    (((& $SQL -noheader $db 'SELECT group_concat(number) FROM (SELECT number FROM work_item WHERE number >= 4 ORDER BY number);') -join '') -replace '\s','') "$Label contiguous assigned series"
  Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) - COUNT(DISTINCT number) FROM work_item;') "$Label no duplicate numbers"
  Assert-Equal 'ok' (& $SQL -noheader $db 'PRAGMA integrity_check;') "$Label integrity after concurrency"
}

function Invoke-Case-T03 {
  Invoke-Race (Join-Path $TMP 't03') 'T03'

  # Part b, the same assertion set against a synced folder. The plan accepts the
  # OneDrive hazard rather than eliminating it, but the runner contract keeps every
  # fixture under $env:TEMP by default, so part b is opt in.
  if ($IncludeOneDrive) {
    $od = 'D:\Cloud\OneDrive\AI\Agentic\plan-code-t03'
    try { Invoke-Race $od 'T03-od' }
    finally { Remove-Item -Recurse -Force $od -ErrorAction SilentlyContinue }
  }
}

# ---------------------------------------------------------------------------
# T04 Git union seeds the candidate upward
# ---------------------------------------------------------------------------

function Invoke-Case-T04 {
  $repo = Join-Path $TMP 't04'
  New-FixtureRepo $repo 3 -SeedDb
  $db = Join-Path $repo 'plans\_plan.db'

  [IO.File]::WriteAllText((Join-Path $repo 'plans\AVRIG-00011-2026-11-20-forced.md'), "# forced`n", [Text.UTF8Encoding]::new($false))
  Assert-Git $repo @('add','-A') 'forced add' | Out-Null
  Assert-Git $repo @('commit','-q','-m','forced 11') 'forced commit' | Out-Null
  Assert-Git $repo @('branch','feat/AVRIG-00011-forced') 'forced branch' | Out-Null
  Assert-Git $repo @('push','-q','origin','main','feat/AVRIG-00011-forced') 'forced push' | Out-Null

  $a = Invoke-Pc $repo @('assign','--title','after git seed','--role','Architect',
                         '--branch','feat/AVRIG-00012-seeded','--plan-path','plans/AVRIG-00012-2026-11-20-seeded.md')
  Assert-Equal 0 $a.Exit 'assign exit'
  Assert-Match $a.Out '"code"\s*:\s*"AVRIG-00012"' 'candidate is git_max + 1'

  # reverse: a database ahead of git must not be pulled backwards
  Assert-Git $repo @('rm','-q','plans/AVRIG-00011-2026-11-20-forced.md') 'drop 11' | Out-Null
  Assert-Git $repo @('commit','-q','-m','drop 11') 'drop 11 commit' | Out-Null
  Assert-Git $repo @('push','-q','origin','main') 'drop 11 push' | Out-Null
  Assert-Git $repo @('branch','-D','feat/AVRIG-00011-forced') 'drop 11 branch' | Out-Null
  Assert-Git $repo @('push','-q','origin','--delete','feat/AVRIG-00011-forced') 'drop 11 branch push' | Out-Null

  $b = Invoke-Pc $repo @('assign','--title','db ahead','--role','Architect',
                         '--branch','feat/AVRIG-00013-ahead','--plan-path','plans/AVRIG-00013-2026-11-20-ahead.md')
  Assert-Equal 0 $b.Exit 'second assign exit'
  Assert-Match $b.Out '"code"\s*:\s*"AVRIG-00013"' 'db max wins when git union regresses'
}

# ---------------------------------------------------------------------------
# T05 Indicator filtering
# ---------------------------------------------------------------------------

function Invoke-Case-T05 {
  $repo = Join-Path $TMP 't05'
  New-FixtureRepo $repo 3 -SeedDb -Prose 'Prose mentions WEB-00009 and AVRIG-00442 and PROJ-00099 and must contribute nothing.'
  $u = [Text.UTF8Encoding]::new($false)

  [IO.File]::WriteAllText((Join-Path $repo 'plans\WEB-00009-2026-11-20-foreign.md'), "# foreign`n", $u)
  [IO.File]::WriteAllText((Join-Path $repo 'plans\AVRIG-00003-2026-11-20-migrate-to-20250-table.md'), "# five digits`n", $u)
  [IO.File]::WriteAllText((Join-Path $repo 'plans\2026-11-20-AVRIG-00442-draft-style.md'), "# draft`n", $u)
  [IO.File]::WriteAllText((Join-Path $repo 'plans\done\WEB-00021-2026-11-20-foreign-done.md'), "# done`n", $u)

  Assert-Git $repo @('add','-A') 'hostile add' | Out-Null
  Assert-Git $repo @('commit','-q','-m','hostile') 'hostile commit' | Out-Null
  Assert-Git $repo @('push','-q','origin','main') 'hostile push' | Out-Null
  Assert-Git $repo @('branch','feat/WEB-00021-foreign') 'foreign branch' | Out-Null
  Assert-Git $repo @('branch','feat/AVRIG-00003-slice/reporting') 'slice branch' | Out-Null
  Assert-Git $repo @('push','-q','origin','feat/WEB-00021-foreign','feat/AVRIG-00003-slice/reporting') 'foreign branch push' | Out-Null

  $db = Join-Path $repo 'plans\_plan.db'
  $a = Invoke-Pc $repo @('assign','--title','filtered','--role','Architect',
                         '--branch','feat/AVRIG-00004-filtered','--plan-path','plans/AVRIG-00004-2026-11-20-filtered.md')
  Assert-Equal 0 $a.Exit 'assign exit'
  Assert-Match $a.Out '"code"\s*:\s*"AVRIG-00004"' 'no inflation from WEB, 20250, 00442, 00021'
  Assert-Equal 0 (& $SQL -noheader $db "SELECT COUNT(*) FROM work_item WHERE indicator <> 'AVRIG';") 'no foreign indicator reached the ledger'
  Assert-Equal 4 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;') 'three seeded rows plus exactly one row written'
}

# ---------------------------------------------------------------------------
# T06 Void burns the number, and a killed assign is all or nothing
# ---------------------------------------------------------------------------

function Invoke-Case-T06 {
  $repo = Join-Path $TMP 't06'
  New-FixtureRepo $repo 0          # no seed row, no coded file, no branch: git_max is 0
  Assert-Equal 0 (Invoke-Pc $repo @('init','--indicator','AVRIG')).Exit 'init exit'
  $db = Join-Path $repo 'plans\_plan.db'

  $a = Invoke-Pc $repo @('assign','--title','to be abandoned','--role','Architect',
                         '--branch','feat/AVRIG-00001-abandoned','--plan-path','plans/AVRIG-00001-2026-11-20-abandoned.md')
  Assert-Equal 0 $a.Exit 'assign exit'
  Assert-Match $a.Out '"code"\s*:\s*"AVRIG-00001"' 'git_max 0 gives the first number'
  Assert-Equal 'committed' (& $SQL -noheader $db 'SELECT state FROM work_item WHERE number=1;') 'a number is committed at the moment it is assigned'
  Assert-Equal 1 (& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='assign' AND number=1;") 'one assign event'

  $v = Invoke-Pc $repo @('void','--code','AVRIG-00001','--reason','plan abandoned')
  Assert-Equal 0 $v.Exit 'void exit'
  Assert-Equal 'voided' (& $SQL -noheader $db 'SELECT state FROM work_item WHERE number=1;') 'state voided'
  Assert-Equal 'plan abandoned' (& $SQL -noheader $db 'SELECT voided_reason FROM work_item WHERE number=1;') 'reason stored verbatim'
  Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item WHERE voided_at IS NULL;') 'voided_at stamped'
  Assert-Equal 1 (& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='void' AND number=1;") 'exactly one void event'
  Assert-Equal 2 (& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;') 'one assign and one void, nothing else'

  $b = Invoke-Pc $repo @('assign','--title','after void','--role','Architect',
                         '--branch','feat/AVRIG-00002-after-void','--plan-path','plans/AVRIG-00002-2026-11-20-after-void.md')
  Assert-Equal 0 $b.Exit 'assign after void'
  Assert-Match $b.Out '"code"\s*:\s*"AVRIG-00002"' 'git_max is still 0, and the voided number is not reissued'
  Assert-Equal 1 (& $SQL -noheader $db "SELECT COUNT(*) FROM work_item WHERE state='voided';") 'the voided row still exists, so the burn is recorded rather than hidden'

  # Part b, a real process kill during assign. One BEGIN IMMEDIATE writes the row and
  # its event, so the only two allowed shapes are both written or neither.
  $killArgs = @(
    '-NoProfile','-File',$PC,'assign','--title','kill me','--role','Architect',
    '--branch','feat/{code}-kill','--plan-path','plans/{code}-2026-11-20-kill.md','--project',$repo)
  $p = Start-Process -FilePath $PW -WindowStyle Hidden -PassThru `
    -ArgumentList ((@($killArgs | ForEach-Object { Format-ProcessArg $_ })) -join ' ')
  Start-Sleep -Milliseconds 250
  Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
  $p.WaitForExit()
  # the sqlite3 child can outlive the killed wrapper for a moment; let it settle
  Start-Sleep -Milliseconds 400

  Assert-Equal 'ok' (& $SQL -noheader $db 'PRAGMA integrity_check;') 'integrity after the kill'
  $rows = [int](& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;')
  $ev   = [int](& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;')
  $n3   = [int](& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item WHERE number = 3;')
  $e3   = [int](& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='assign' AND number = 3;")
  Add-Log "T06 kill shape rows=$rows events=$ev n3=$n3 e3=$e3"

  if ($rows -eq 3) {
    Assert-Equal 'committed' (& $SQL -noheader $db 'SELECT state FROM work_item WHERE number = 3;') 'the surviving row is committed'
    Assert-Equal 4 $ev 'three events before the kill plus the one committed with the row'
    Assert-Equal 1 $n3 'the row of the killed assign exists'
    Assert-Equal 1 $e3 'the event of the killed assign was committed with it'
  } elseif ($rows -eq 2) {
    Assert-Equal 3 $ev 'no event without its row'
    Assert-Equal 0 $n3 'the killed assign left no row'
    Assert-Equal 0 $e3 'the killed assign left no event'
  } else {
    throw "T06 : unexpected row count $rows after the kill"
  }

  # the next number continues from whatever survived, never backwards, never twice
  $before = [int](& $SQL -noheader $db 'SELECT COALESCE(MAX(number),0) FROM work_item;')
  $d = Invoke-Pc $repo @('assign','--dry-run','--title','after kill','--role','Architect',
                         '--branch','feat/{code}-after','--plan-path','plans/{code}-2026-11-20-after.md')
  Assert-Equal 0 $d.Exit 'dry run after the kill'
  Assert-Match $d.Out ('"code"\s*:\s*"AVRIG-{0:D5}"' -f ($before + 1)) 'strictly increasing after the kill'
  Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) - COUNT(DISTINCT number) FROM work_item;') 'no duplicate numbers'
}

# ---------------------------------------------------------------------------
# T07 Injection through the JSON payload path, and the payload read shape
# ---------------------------------------------------------------------------

function Invoke-PayloadProbe([string]$Db, [string]$Path) {
  $sqlText = ".bail on`n.timeout 5000`n.parameter set :payload '$Path'`n" +
             "SELECT json_extract(value,'`$.title') FROM json_each(readfile(:payload));`n"
  $o = ($sqlText | & $SQL -noheader $Db 2>&1) -join "`n"
  [pscustomobject]@{ Exit = $LASTEXITCODE; Out = $o }
}

function Invoke-Case-T07 {
  $repo = Join-Path $TMP 't07'
  New-FixtureRepo $repo 3
  Assert-Equal 0 (Invoke-Pc $repo @('init','--indicator','AVRIG')).Exit 'init exit'
  $db = Join-Path $repo 'plans\_plan.db'

  $title  = "It's a `"quoted`" title'; DROP TABLE work_item; --"
  $reason = 'push rejected; "non-fast-forward"'

  $a = Invoke-Pc $repo @('assign','--title',$title,'--role','Architect',
                         '--branch','feat/AVRIG-00004-inject','--plan-path','plans/AVRIG-00004-2026-11-20-inject.md')
  Assert-Equal 0 $a.Exit 'assign exit'
  $stored = (& $SQL -noheader $db 'SELECT title FROM work_item ORDER BY number DESC LIMIT 1;')
  Assert-Equal $title $stored 'title verbatim'
  Assert-Equal 3 (& $SQL -noheader $db "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('project','work_item','allocation_event');") 'tables survive'

  $v = Invoke-Pc $repo @('void','--code','AVRIG-00004','--reason',$reason)
  Assert-Equal 0 $v.Exit 'void exit'
  Assert-Equal $reason (& $SQL -noheader $db 'SELECT voided_reason FROM work_item WHERE number=4;') 'reason verbatim'
  Assert-Equal 1 (& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='void' AND number=4;") 'one void event, with no injected text in its own statement'
  Assert-Equal 'ok' (& $SQL -noheader $db 'PRAGMA integrity_check;') 'integrity'

  # Part b, the payload envelope and read shape are pinned here.
  $json  = '[{"indicator":"AVRIG","title":"bom probe"}]'   # one element array, B1
  $obj   = '{"indicator":"AVRIG","title":"bom probe"}'     # the shape that must fail
  $plain = Join-Path $repo 'plain.json'
  $bom   = Join-Path $repo 'bom.json'
  $objf  = Join-Path $repo 'obj.json'
  $empty = Join-Path $repo 'empty.json'
  $ps7   = Join-Path $repo 'ps7-plain.json'

  [IO.File]::WriteAllText($plain, $json, [Text.UTF8Encoding]::new($false))
  [IO.File]::WriteAllText($objf,  $obj,  [Text.UTF8Encoding]::new($false))
  [IO.File]::WriteAllText($empty, '',    [Text.UTF8Encoding]::new($false))
  Set-Content -Path $ps7   -Value $json -Encoding utf8
  Set-Content -Path $bom   -Value $json -Encoding utf8BOM

  Assert-Equal 91 ([IO.File]::ReadAllBytes($ps7)[0]) 'pwsh 7 utf8 writes no BOM (first byte is the [ of the array)'
  Assert-Equal 239 ([IO.File]::ReadAllBytes($bom)[0]) 'utf8BOM writes the BOM'

  $ok = Invoke-PayloadProbe $db $plain
  Assert-Equal 0 $ok.Exit 'array envelope is accepted'
  Assert-Equal 'bom probe' $ok.Out 'array envelope yields the title'

  $b = Invoke-PayloadProbe $db $bom
  Assert-Equal 0 $b.Exit 'BOM prefixed array still parses (C3)'
  Assert-Equal 'bom probe' $b.Out 'BOM is tolerated by SQLite'

  $bad = Invoke-PayloadProbe $db $objf
  Assert-Equal 1 $bad.Exit 'object envelope is SQLITE_ERROR'
  Assert-Match $bad.Out 'malformed JSON' 'object envelope fails as measured'

  $em = Invoke-PayloadProbe $db $empty
  Assert-Equal 1 $em.Exit 'empty payload is SQLITE_ERROR'
  Assert-Match $em.Out 'malformed JSON' 'empty payload message'
}

# ---------------------------------------------------------------------------
# T08 Import rebuilds from the durable dump
# ---------------------------------------------------------------------------

function Invoke-Case-T08 {
  $repo = Join-Path $TMP 't08'
  New-FixtureRepo $repo 3 -SeedDb -ExportDump
  $db = Join-Path $repo 'plans\_plan.db'
  $dump = Join-Path $repo 'plans\_plan.sql'

  $a = Invoke-Pc $repo @('assign','--title','before delete','--role','Architect',
                         '--branch','feat/AVRIG-00004-x','--plan-path','plans/AVRIG-00004-2026-11-20-x.md','--issue','99')
  Assert-Equal 0 $a.Exit 'assign exit'
  Assert-Match $a.Out '"code"\s*:\s*"AVRIG-00004"' 'pre-deletion candidate'
  Assert-Equal 0 (Invoke-Export $repo).Exit 'export exit'
  Assert-Equal 4 ([int](& $SQL -noheader $db 'SELECT COALESCE(MAX(number),0) FROM work_item;')) 'db max after assign'
  $expected = (& $SQL -noheader $db 'SELECT COALESCE(MAX(number),0)+1 FROM work_item;')

  Remove-Item -Force -ErrorAction SilentlyContinue -Path @($db, "$db-wal", "$db-shm")
  Assert-Equal 0 (Invoke-Pc $repo @('import','--indicator','AVRIG')).Exit 'import exit'

  Assert-Equal 4 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;') 'row count after import'
  Assert-Equal 'AVRIG-00001,AVRIG-00002,AVRIG-00003,AVRIG-00004' `
    (((& $SQL -noheader $db 'SELECT group_concat(code) FROM (SELECT code FROM work_item ORDER BY number);') -join '') -replace '\s','') 'codes match the dump'
  Assert-Equal 4 ([int](& $SQL -noheader $db 'SELECT COALESCE(MAX(number),0) FROM work_item;')) 'db max matches the dump'

  # idempotency: a second import changes no row, writes no event, and moves no byte
  $digestSql = "SELECT group_concat(code||'|'||number||'|'||state||'|'||COALESCE(committed_at,''),';') FROM (SELECT * FROM work_item ORDER BY number);"
  $digest = (& $SQL -noheader $db $digestSql)
  $events = [int](& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;')
  Assert-Equal 0 (Invoke-Export $repo).Exit 'export after rebuild'
  $dumpA = "$dump.first"
  Copy-Item -LiteralPath $dump -Destination $dumpA -Force

  Assert-Equal 0 (Invoke-Pc $repo @('import','--indicator','AVRIG')).Exit 'second import exit'
  Assert-Equal $digest (& $SQL -noheader $db $digestSql) 'second import changed no row'
  Assert-Equal $events ([int](& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;')) 'second import wrote no event'
  Assert-Equal 0 (Invoke-Export $repo).Exit 'export after second import'
  Assert-SameBytes $dumpA $dump 'second import and export produced no output change'

  $b = Invoke-Pc $repo @('assign','--title','after import','--role','Architect',
                         '--branch','feat/AVRIG-00005-y','--plan-path','plans/AVRIG-00005-2026-11-20-y.md')
  Assert-Equal 0 $b.Exit 'assign after import'
  Assert-Match $b.Out ('"code"\s*:\s*"AVRIG-{0:D5}"' -f [int]$expected) 'allocation unchanged by deletion'
}

# ---------------------------------------------------------------------------
# T09 Dump determinism and round-trip
# ---------------------------------------------------------------------------

function Invoke-Case-T09 {
  $repo = Join-Path $TMP 't09'
  New-FixtureRepo $repo 0
  Assert-Equal 0 (Invoke-Pc $repo @('init','--indicator','AVRIG')).Exit 'init exit'
  $db = Join-Path $repo 'plans\_plan.db'
  $dump = Join-Path $repo 'plans\_plan.sql'

  # a SQL injection attempt, a single quote, and a backslash all travel as JSON
  # values and must survive the dump round trip unchanged
  $h1 = 'It''s a "quoted" title''; DROP TABLE work_item; --'
  $h2 = 'path C:\tmp\plan ''quoted'' with \ backslash'

  $a = Invoke-Pc $repo @('assign','--title',$h1,'--role','Architect',
                         '--branch','feat/{code}-hostile','--plan-path','plans/{code}-2026-11-20-hostile.md')
  Assert-Equal 0 $a.Exit 'assign hostile exit'
  $b = Invoke-Pc $repo @('assign','--title',$h2,'--role','Architect',
                         '--branch','feat/{code}-backslash','--plan-path','plans/{code}-2026-11-20-backslash.md')
  Assert-Equal 0 $b.Exit 'assign backslash exit'

  # the hostile text travels in the title, not the pointer, so the files the two rows
  # name are real: a committed row pointing at nothing is drift in its own right
  New-PlanFile $repo 'plans/AVRIG-00001-2026-11-20-hostile.md' | Out-Null
  New-PlanFile $repo 'plans/AVRIG-00002-2026-11-20-backslash.md' | Out-Null

  Assert-Equal 0 (Invoke-Export $repo).Exit 'first export exit'
  Assert-True (Test-Path -LiteralPath $dump) 'export produced plans/_plan.sql'
  Assert-NoBom $dump 'the dump is BOM free UTF-8'
  $sha1 = Get-Sha256 $dump

  # export twice is byte identical: determinism is a property a hash decides
  Assert-Equal 0 (Invoke-Export $repo).Exit 'second export exit'
  Assert-Equal $sha1 (Get-Sha256 $dump) 'export twice is byte identical'

  Assert-Equal $h1 (& $SQL -noheader $db 'SELECT title FROM work_item WHERE number=1;') 'the injected title is stored verbatim'
  Assert-Equal $h2 (& $SQL -noheader $db 'SELECT title FROM work_item WHERE number=2;') 'the backslash title is stored verbatim'

  # export of an imported dump reproduces that dump byte for byte
  Remove-Item -Force -ErrorAction SilentlyContinue -Path @($db, "$db-wal", "$db-shm")
  Assert-Equal 0 (Invoke-Pc $repo @('import','--indicator','AVRIG')).Exit 'import from dump exit'
  Assert-Equal 2 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;') 'both rows rebuilt from the dump'
  Assert-Equal $h1 (& $SQL -noheader $db 'SELECT title FROM work_item WHERE number=1;') 'the injected title survived the round trip'
  Assert-Equal $h2 (& $SQL -noheader $db 'SELECT title FROM work_item WHERE number=2;') 'the backslash title survived the round trip'
  Assert-Equal 0 (Invoke-Export $repo).Exit 'export after import exit'
  Assert-Equal $sha1 (Get-Sha256 $dump) 'export of an imported dump reproduces it byte for byte'

  # and a clean checkout is not drift
  Assert-Equal 0 (Invoke-Pc $repo @('verify','--strict')).Exit 'verify is clean after the round trip'
}

# ---------------------------------------------------------------------------
# T10 Verify detects drift in both directions
# ---------------------------------------------------------------------------

function Invoke-Case-T10 {
  # (a) a database row that the dump does not carry: assign without exporting
  $repo = Join-Path $TMP 't10a'
  New-FixtureRepo $repo 3 -SeedDb -ExportDump
  $db = Join-Path $repo 'plans\_plan.db'

  $a = Invoke-Pc $repo @('assign','--title','now in db','--role','Architect',
                         '--branch','feat/AVRIG-00004-now-in-db','--plan-path','plans/AVRIG-00004-2026-11-20-now-in-db.md')
  Assert-Equal 0 $a.Exit 'part a assign exit'
  New-PlanFile $repo 'plans/AVRIG-00004-2026-11-20-now-in-db.md' | Out-Null
  Assert-Equal 0 (Invoke-Export $repo).Exit 'part a export exit'
  Assert-Equal 0 (Invoke-Pc $repo @('verify','--strict')).Exit 'clean baseline'

  # a row that export would include but the committed dump does not
  $ins = "INSERT INTO work_item (indicator,number,title,state,owner_role,claiming_branch,plan_path,committed_at,created_on,actor_host,actor_user) " +
         "VALUES ('AVRIG',7,'only in db','committed','Architect','feat/AVRIG-00007-only-in-db','plans/AVRIG-00007-2026-11-20-only-in-db.md','2026-11-20T00:00:00.000Z','2026-11-20','h','u');"
  $io = (& $SQL -bail $db $ins 2>&1) -join "`n"
  Assert-Equal 0 $LASTEXITCODE "seed the db-only row : $io"
  New-PlanFile $repo 'plans/AVRIG-00007-2026-11-20-only-in-db.md' | Out-Null

  # The finding must be labelled and must name the artifact that disagrees, not just
  # fail. Remedy advice is deliberately not graded here: what the two directions need
  # differs, so the case grades that each direction is detected, reported, and
  # resolved by the operation its own direction actually calls for.
  $v = Invoke-Pc $repo @('verify','--strict')
  Assert-Equal 1 $v.Exit 'strict fails on a db-only row'
  Assert-Match $v.Out 'drift:' 'strict labels the finding as drift'
  Assert-Match $v.Out '_plan\.sql' 'strict names the artifact that disagrees'
  $w = Invoke-Pc $repo @('verify')
  Assert-Equal 0 $w.Exit 'non strict reports without failing'
  Assert-Match $w.Out '_plan\.sql' 'non strict still names the artifact'
  Assert-Equal 5 ([int](& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;')) 'verify did not mutate the database'

  # the direction that the database leads in is resolved by export, and only then
  # does strict mode come back clean
  Assert-Equal 0 (Invoke-Export $repo).Exit 'export after the drift'
  Assert-True (@(Select-String -Path (Join-Path $repo 'plans\_plan.sql') -Pattern 'AVRIG-00007').Count -ge 1) 'the exported dump now carries the database-only row'
  Assert-Equal 0 (Invoke-Pc $repo @('verify','--strict')).Exit 'export resolves a db-only row'

  # (b) a dump row that the database does not carry: copy in a larger dump
  $repo2 = Join-Path $TMP 't10b'
  New-FixtureRepo $repo2 3 -SeedDb -ExportDump
  $db2 = Join-Path $repo2 'plans\_plan.db'
  $dump2 = Join-Path $repo2 'plans\_plan.sql'
  $a2 = Invoke-Pc $repo2 @('assign','--title','dump-only','--role','Architect',
                           '--branch','feat/AVRIG-00004-dump-only','--plan-path','plans/AVRIG-00004-2026-11-20-dump-only.md')
  Assert-Equal 0 $a2.Exit 'part b assign exit'
  New-PlanFile $repo2 'plans/AVRIG-00004-2026-11-20-dump-only.md' | Out-Null
  Assert-Equal 0 (Invoke-Export $repo2).Exit 'part b export exit'
  Assert-Equal 4 ([int](& $SQL -noheader $db2 'SELECT COUNT(*) FROM work_item;')) 'the database holds four rows'

  # build a dump that carries one more row than the database, without hand editing
  $src = Join-Path $TMP 't10b-src'
  New-FixtureRepo $src 5 -SeedDb -ExportDump
  Copy-Item -LiteralPath (Join-Path $src 'plans\_plan.sql') -Destination $dump2 -Force
  $dumpCopy = "$dump2.before"
  Copy-Item -LiteralPath $dump2 -Destination $dumpCopy -Force
  # the dump carries five rows, and each names its own plan file: without them the drift
  # under test would be a second, unrelated finding about a missing pointer
  for ($n = 1; $n -le 5; $n++) { New-PlanFile $repo2 (Get-FixturePlanPath $n) | Out-Null }

  $v2 = Invoke-Pc $repo2 @('verify','--strict')
  Assert-Equal 1 $v2.Exit 'strict fails on a dump-only row'
  Assert-Match $v2.Out 'drift:' 'the second direction is also labelled drift'
  Assert-Match $v2.Out '_plan\.sql' 'the second direction names the artifact'
  Assert-Equal 4 ([int](& $SQL -noheader $db2 'SELECT COUNT(*) FROM work_item;')) 'verify did not mutate the database'

  # the direction that the dump leads in is resolved by import, which is what makes
  # the dump the durable record rather than a mirror of whatever the database holds
  Assert-Equal 0 (Invoke-Pc $repo2 @('import','--indicator','AVRIG')).Exit 'import after the drift'
  Assert-Equal 5 ([int](& $SQL -noheader $db2 'SELECT COUNT(*) FROM work_item;')) 'import recovered the dump-only row'
  Assert-Equal 1 ([int](& $SQL -noheader $db2 "SELECT COUNT(*) FROM work_item WHERE code='AVRIG-00005';")) 'the recovered row is the one the dump carried'
  Assert-SameBytes $dumpCopy $dump2 'import did not rewrite the dump'
  Assert-Equal 0 (Invoke-Pc $repo2 @('verify','--strict')).Exit 'import resolves a dump-only row'
}

# ---------------------------------------------------------------------------
# T11 Missing sqlite3 is a configuration failure
# ---------------------------------------------------------------------------

function Invoke-Case-T11 {
  $repo = Join-Path $TMP 't11'
  New-FixtureRepo $repo 3
  Assert-Equal 0 (Invoke-Pc $repo @('init','--indicator','AVRIG')).Exit 'init exit'
  $db = Join-Path $repo 'plans\_plan.db'
  $before = (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;')

  $probe = @'
$env:PATH = 'C:\Windows\System32;C:\Windows'
Remove-Item Env:AVRIG_SQLITE3 -ErrorAction SilentlyContinue
& '__PW__' -NoProfile -File '__PC__' assign --title t --role Architect --branch 'feat/{code}-t' --plan-path 'plans/{code}-2026-11-20-t.md' --project '__REPO__'
exit $LASTEXITCODE
'@
  $probe = $probe.Replace('__PW__', $PW).Replace('__PC__', $PC).Replace('__REPO__', $repo)
  $probePath = Join-Path $repo 'probe.ps1'
  [IO.File]::WriteAllText($probePath, $probe, [Text.UTF8Encoding]::new($false))

  $o = (& $PW -NoProfile -File $probePath 2>&1) -join "`n"
  $code = $LASTEXITCODE
  Add-Log "T11 probe exit=$code`n$o"
  Assert-Equal 3 $code 'exit 3 on missing binary'
  Assert-Match $o 'sqlite3' 'message names the binary'
  Assert-Equal $before (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;') 'no row written'
  Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;') 'no event written'
}

# ---------------------------------------------------------------------------
# T12 Dry run writes nothing
# ---------------------------------------------------------------------------

function Invoke-Case-T12 {
  $repo = Join-Path $TMP 't12'
  New-FixtureRepo $repo 3
  Assert-Equal 0 (Invoke-Pc $repo @('init','--indicator','AVRIG')).Exit 'init exit'
  $db = Join-Path $repo 'plans\_plan.db'

  $before = [int](& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;')
  $ev = [int](& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;')
  $d = Invoke-Pc $repo @('assign','--dry-run','--title','preview','--role','Architect',
                         '--branch','feat/{code}-preview','--plan-path','plans/{code}-2026-11-20-preview.md')
  Assert-Equal 0 $d.Exit 'dry run exit'
  Assert-Match $d.Out '"code"\s*:\s*"AVRIG-00004"' 'candidate printed'
  Assert-Equal $before ([int](& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;')) 'row count unchanged'
  Assert-Equal $ev ([int](& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;')) 'event count unchanged'

  $a = Invoke-Pc $repo @('assign','--title','real','--role','Architect',
                         '--branch','feat/AVRIG-00004-real','--plan-path','plans/AVRIG-00004-2026-11-20-real.md')
  Assert-Equal 0 $a.Exit 'real assign exit'
  Assert-Match $a.Out '"code"\s*:\s*"AVRIG-00004"' 'the real assign still gets the same number'
}

# ---------------------------------------------------------------------------
# T13 assign writes one row and one event, or neither
# ---------------------------------------------------------------------------

function Invoke-Case-T13 {
  $repo = Join-Path $TMP 't13'
  New-FixtureRepo $repo 3
  Assert-Equal 0 (Invoke-Pc $repo @('init','--indicator','AVRIG')).Exit 'init exit'
  $db = Join-Path $repo 'plans\_plan.db'

  $a = Invoke-Pc $repo @('assign','--title','one row','--role','Architect',
                         '--branch','feat/AVRIG-00004-one','--plan-path','plans/AVRIG-00004-2026-11-20-one.md','--issue','42')
  Assert-Equal 0 $a.Exit 'assign exit'
  Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item WHERE number=4;') 'exactly one row'
  Assert-Equal 1 (& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='assign' AND number=4;") 'exactly one assign event'
  Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;') 'the call wrote one row and no more'
  Assert-Equal 0 (& $SQL -noheader $db "SELECT COUNT(*) FROM work_item w WHERE NOT EXISTS (SELECT 1 FROM allocation_event e WHERE e.event='assign' AND e.indicator=w.indicator AND e.number=w.number);") 'every row carries its own assign event'

  $rows = [int](& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;')
  $ev   = [int](& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='assign';")
  Assert-Equal $rows $ev 'one assign event per row, no more'

  # a refused assign writes neither, and the row that already exists is untouched
  $bad = Invoke-Pc $repo @('assign','--title','refused','--role','Architect',
                           '--branch','feat/AVRIG-00009-other','--plan-path','plans/AVRIG-00009-2026-11-20-other.md')
  Assert-Equal 3 $bad.Exit 'a branch naming another code is refused'
  Assert-Equal $rows ([int](& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;')) 'refused assign wrote no row'
  Assert-Equal $ev ([int](& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='assign';")) 'refused assign wrote no event'
  Assert-Equal 0 ([int](& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item WHERE number=9;')) 'no row exists for the code the branch named'
  Assert-Equal 'committed' (& $SQL -noheader $db 'SELECT state FROM work_item WHERE number=4;') 'the earlier row is untouched'
}

# ---------------------------------------------------------------------------
# T14 Approval runbook end to end
# ---------------------------------------------------------------------------

function Invoke-Case-T14 {
  $repo = Join-Path $TMP 't14\scratch'
  New-FixtureRepo $repo 3 -SeedDb -ExportDump
  $db = Join-Path $repo 'plans\_plan.db'
  $dump = Join-Path $repo 'plans\_plan.sql'

  [IO.File]::WriteAllText((Join-Path $repo 'plans\2026-11-20-demo-task.md'), "# demo`n", [Text.UTF8Encoding]::new($false))
  Assert-Git $repo @('add','-A') 'draft add' | Out-Null
  Assert-Git $repo @('commit','-q','-m','draft') 'draft commit' | Out-Null

  # 1. assign: one call claims the number and binds it to the branch and plan path
  $a = Invoke-Pc $repo @('assign','--title','Demo Task','--role','Architect',
                         '--branch','feat/{code}-demo-task','--plan-path','plans/{code}-2026-11-20-demo-task.md',
                         '--issue','123')
  Assert-Equal 0 $a.Exit 'assign'
  $code = Get-Code $a.Out
  Assert-Equal 'AVRIG-00004' $code 'assigned code'

  # 2. export the durable archive, then rename the draft to the coded name and cut the branch
  Assert-Equal 0 (Invoke-Export $repo).Exit 'export'
  Assert-Git $repo @('mv','plans/2026-11-20-demo-task.md',"plans/$code-2026-11-20-demo-task.md") 'rename draft' | Out-Null
  Assert-Git $repo @('branch',"feat/$code-demo-task") 'claiming branch' | Out-Null

  # 3. cross check database, dump, and git union
  Assert-Equal 0 (Invoke-Pc $repo @('verify','--strict')).Exit 'verify after runbook'

  Assert-Equal 1 ([int](& $SQL -noheader $db "SELECT COUNT(*) FROM work_item WHERE code='$code';")) 'one database row for the code'
  Assert-True (@(Select-String -Path $dump -Pattern ([regex]::Escape($code))).Count -ge 1) 'the dump carries the code'
  Assert-Equal 1 (@(Get-ChildItem (Join-Path $repo 'plans') -Filter "$code-*.md").Count) 'one coded plan file'
  Assert-Equal 1 (@(git -C $repo branch --format='%(refname:short)' | Where-Object { $_ -match [regex]::Escape($code) }).Count) 'one claiming branch'

  Assert-Git $repo @('add','-A') 'approval add' | Out-Null
  Assert-Git $repo @('commit','-q','-m',"docs($code): allocate") 'approval commit' | Out-Null
  $touched = @(git -C $repo show --name-only --format= HEAD)
  Assert-Equal 1 (@($touched | Where-Object { $_ -like "plans/$code-*.md" }).Count) 'approval commit carries the coded plan'
  Assert-Equal 1 (@($touched | Where-Object { $_ -eq 'plans/_plan.sql' }).Count) 'approval commit carries the dump'

  $n = Invoke-Pc $repo @('assign','--dry-run','--title','Next','--role','Architect',
                         '--branch','feat/{code}-next','--plan-path','plans/{code}-2026-11-20-next.md')
  Assert-Equal 0 $n.Exit 'dry run exit'
  Assert-Match $n.Out '"code"\s*:\s*"AVRIG-00005"' 'next code advances'
}

# ---------------------------------------------------------------------------
# T15 Exit code contract
# ---------------------------------------------------------------------------

function Invoke-Case-T15 {
  $repo = Join-Path $TMP 't15'
  New-FixtureRepo $repo 3
  Assert-Equal 0 (Invoke-Pc $repo @('init','--indicator','AVRIG')).Exit 'init exit'
  $db = Join-Path $repo 'plans\_plan.db'

  # a complete legal bind for AVRIG-00004, the number this fixture would issue
  $ok4 = @('--title','t','--role','Architect',
           '--branch','feat/AVRIG-00004-x','--plan-path','plans/AVRIG-00004-2026-11-20-x.md')

  Assert-Equal 3 (Invoke-Pc $repo @('assign','--title','','--role','Architect',
    '--branch','feat/AVRIG-00004-x','--plan-path','plans/AVRIG-00004-2026-11-20-x.md')).Exit 'empty title'
  Assert-Equal 3 (Invoke-Pc $repo (@('assign','--indicator','avrig') + $ok4)).Exit 'lowercase indicator'
  Assert-Equal 3 (Invoke-Pc $repo @('assign','--nonsense','1')).Exit 'unknown flag'
  Assert-Equal 3 (Invoke-Pc $repo @('void','--code','AVRIG-09999','--reason','nope')).Exit 'unknown code'

  # the input refusals assign now has: the branch, the plan path, the issue number
  Assert-Equal 3 (Invoke-Pc $repo @('assign','--title','t','--role','Architect',
    '--branch','feat/AVRIG-00009-other','--plan-path','plans/AVRIG-00009-2026-11-20-other.md')).Exit 'branch carrying another code'
  Assert-Equal 3 (Invoke-Pc $repo @('assign','--title','t','--role','Architect',
    '--branch','feat/AVRIG-00004-x','--plan-path','other/AVRIG-00004-2026-11-20-x.md')).Exit 'plan path outside plans'
  Assert-Equal 3 (Invoke-Pc $repo @('assign','--title','t','--role','Architect',
    '--branch','feat/AVRIG-00004-x','--plan-path','plans/AVRIG-00004-2026-11-20-x.txt')).Exit 'plan path not markdown'
  Assert-Equal 3 (Invoke-Pc $repo (@('assign') + $ok4 + @('--issue','abc'))).Exit 'non numeric issue'

  Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;') 'no refusal wrote a row'
  Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;') 'no refusal wrote an event'

  # case A: no origin remote configured, a warning unless --strict-git is asked for.
  # With no remote, the default branch contract resolves at step 4, which needs exactly
  # one local branch, so the coded fixture branch is dropped.
  $gorp = Join-Path $TMP 't15\noorigin'
  New-FixtureRepo $gorp 3
  Assert-Git $gorp @('remote','remove','origin') 'remove origin' | Out-Null
  Assert-Git $gorp @('branch','-D','feat/AVRIG-00003-fixture-branch') 'single local branch' | Out-Null
  Assert-Equal 0 (Invoke-Pc $gorp @('init','--indicator','AVRIG')).Exit 'no-origin init exit'
  $gdb = Join-Path $gorp 'plans\_plan.db'

  $r = Invoke-Pc $gorp @('assign','--title','no origin','--role','Architect',
    '--branch','feat/AVRIG-00004-no-origin','--plan-path','plans/AVRIG-00004-2026-11-20-no-origin.md')
  Assert-Equal 0 $r.Exit 'no origin is a warning by default'
  Assert-Match $r.Out 'warn' 'warning recorded'

  $s = Invoke-Pc $gorp @('assign','--title','no origin strict','--role','Architect',
    '--branch','feat/AVRIG-00005-no-origin','--plan-path','plans/AVRIG-00005-2026-11-20-no-origin.md','--strict-git')
  Assert-Equal 4 $s.Exit 'no origin under --strict-git'
  Assert-Equal 1 (& $SQL -noheader $gdb 'SELECT COUNT(*) FROM work_item;') 'only the lax run wrote a row'

  # case B: origin configured but the fetch fails, which is exit 4 with no flag at all
  $forp = Join-Path $TMP 't15\badremote'
  New-FixtureRepo $forp 3
  Assert-Equal 0 (Invoke-Pc $forp @('init','--indicator','AVRIG')).Exit 'bad-remote init exit'
  Assert-Git $forp @('remote','set-url','origin',(Join-Path $TMP 't15\missing-origin.git')) 'bad remote url' | Out-Null
  Assert-Git $forp @('update-ref','-d','refs/remotes/origin/main') 'drop cached remote ref' | Out-Null
  $fdb = Join-Path $forp 'plans\_plan.db'

  $f = Invoke-Pc $forp @('assign','--title','bad remote','--role','Architect',
    '--branch','feat/AVRIG-00004-bad-remote','--plan-path','plans/AVRIG-00004-2026-11-20-bad-remote.md')
  Assert-Equal 4 $f.Exit 'attempted fetch failure is exit 4 unconditionally'
  Assert-Equal 0 (& $SQL -noheader $fdb 'SELECT COUNT(*) FROM work_item;') 'failed fetch wrote no row'

  $n = Invoke-Pc $forp @('assign','--title','bad remote nofetch','--role','Architect',
    '--branch','feat/AVRIG-00004-bad-remote-nofetch','--plan-path','plans/AVRIG-00004-2026-11-20-bad-remote-nofetch.md','--no-fetch')
  Assert-Equal 0 $n.Exit '--no-fetch bypasses the fetch and succeeds'

  $j = Invoke-Pc $repo @('status','--json')
  Assert-Equal 0 $j.Exit 'status exit'
  Assert-Equal 0 (@(Get-StatusRows $j.Out).Count) 'every refusal left the ledger empty'
}

# ---------------------------------------------------------------------------
# T16 The database never reaches git, and the dump is not ignored
# ---------------------------------------------------------------------------

function Invoke-Case-T16 {
  Assert-True (Test-Path -LiteralPath $WT) 'the tree under test exists'
  Push-Location $WT
  try {
    foreach ($f in @('_plan.db','_plan.db-wal','_plan.db-shm')) {
      $o = (& git check-ignore -v "plans/$f" 2>&1) -join "`n"
      $code = $LASTEXITCODE
      Add-Log "T16 check-ignore plans/$f exit=$code : $o"
      Assert-Equal 0 $code "plans/$f is ignored"
      Assert-Match $o '\.gitignore:' "plans/$f is named by a .gitignore rule"
    }
    $dumpCode = (& git check-ignore -q 'plans/_plan.sql' 2>&1)
    $dumpIgnored = ($LASTEXITCODE -eq 0)
    Assert-True (-not $dumpIgnored) 'plans/_plan.sql is tracked content, not ignored'
    $porcelain = @(git status --porcelain plans/ | Where-Object { $_ -match '_plan\.db' })
    Assert-Equal 0 $porcelain.Count 'the database is not reported by git status'
    $tracked = @(git ls-files plans/ | Select-String '_plan\.db')
    Assert-Equal 0 $tracked.Count 'the database is never tracked'
  } finally {
    Pop-Location
  }
}

# ---------------------------------------------------------------------------
# T17 Status and explicit void
# ---------------------------------------------------------------------------

function Invoke-Case-T17 {
  $repo = Join-Path $TMP 't17'
  New-FixtureRepo $repo 1 -SeedDb -ExportDump
  $db = Join-Path $repo 'plans\_plan.db'

  # the fixture's durable archive is the seed source: drop the database and rebuild
  Remove-Item -Force -ErrorAction SilentlyContinue -Path @($db, "$db-wal", "$db-shm")
  Assert-Equal 0 (Invoke-Pc $repo @('import','--indicator','AVRIG')).Exit 'import from the seeded dump'
  Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;') 'the seeded dump rebuilt one row'

  $a = Invoke-Pc $repo @('assign','--title','void me','--role','Architect',
                         '--branch','feat/AVRIG-00002-void-me','--plan-path','plans/AVRIG-00002-2026-11-20-void-me.md')
  Assert-Equal 0 $a.Exit 'assign exit'
  Assert-Equal 'AVRIG-00002' (Get-Code $a.Out) 'the seeded row advances the number'

  $s = Get-StatusRows (Invoke-Pc $repo @('status','--json')).Out
  Assert-Equal 2 (@($s).Count) 'two rows listed'
  $row = @($s | Where-Object { $_.code -eq 'AVRIG-00002' })
  Assert-Equal 1 $row.Count 'the assigned row is present under its code'
  Assert-Equal 'committed' $row[0].state 'state reported'
  Assert-Equal 'feat/AVRIG-00002-void-me' $row[0].claiming_branch 'claiming branch reported under its snake_case name'
  Assert-True ($null -eq $row[0].voided_reason) 'voided_reason is null on a live row'

  Assert-Equal 0 (Invoke-Pc $repo @('void','--code','AVRIG-00002','--reason','push rejected')).Exit 'void exit'
  Assert-Equal 'voided' (& $SQL -noheader $db 'SELECT state FROM work_item WHERE number=2;') 'state voided'
  Assert-Equal 'push rejected' (& $SQL -noheader $db 'SELECT voided_reason FROM work_item WHERE number=2;') 'reason stored'
  Assert-Equal 1 (& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='void' AND number=2;") 'one void event'

  $s2 = Get-StatusRows (Invoke-Pc $repo @('status','--json')).Out
  $row2 = @($s2 | Where-Object { $_.code -eq 'AVRIG-00002' })
  Assert-Equal 'voided' $row2[0].state 'status reports the transition rather than the assignment'
  Assert-Equal 'push rejected' $row2[0].voided_reason 'status carries the reason'

  $b = Invoke-Pc $repo @('assign','--title','after void','--role','Architect',
                         '--branch','feat/AVRIG-00003-after-void','--plan-path','plans/AVRIG-00003-2026-11-20-after-void.md')
  Assert-Equal 0 $b.Exit 'assign after void exit'
  Assert-Equal 'AVRIG-00003' (Get-Code $b.Out) 'the voided number is not reissued'

  $s3 = Get-StatusRows (Invoke-Pc $repo @('status','--json')).Out
  Assert-Equal 3 (@($s3).Count) 'the seeded row, the voided row, and its successor are all listed'

  # Row lines are matched at column 0, so a detail line echoing the code does not
  # read as a second row. Both views are asserted, because a filter that lists
  # everything would pass a single view check.
  $committedView = (Invoke-Pc $repo @('status','--state','committed')).Out
  $voidedView    = (Invoke-Pc $repo @('status','--state','voided')).Out
  Assert-Equal 0 ([regex]::Matches($committedView, '(?m)^AVRIG-00002\s').Count) 'the burned number has no row in the committed view'
  Assert-Equal 1 ([regex]::Matches($committedView, '(?m)^AVRIG-00003\s').Count) 'its successor does have a row in the committed view'
  Assert-Equal 0 ([regex]::Matches($voidedView, '(?m)^AVRIG-00003\s').Count) 'the committed successor stays out of the voided view'
  Assert-Equal 1 ([regex]::Matches($voidedView, '(?m)^AVRIG-00002\s').Count) 'the state filter lists the voided row exactly once'
}

# ---------------------------------------------------------------------------
# T18 init is idempotent and refuses a foreign or newer schema
# ---------------------------------------------------------------------------

function Invoke-Case-T18 {
  $repo = Join-Path $TMP 't18'
  New-FixtureRepo $repo 0
  Assert-Equal 0 (Invoke-Pc $repo @('init','--indicator','AVRIG')).Exit 'first init exit'
  $db = Join-Path $repo 'plans\_plan.db'
  $dump = Join-Path $repo 'plans\_plan.sql'

  # A repeat init must be safe: it may be a no-op or an explicit refusal naming the
  # durable record, but it must never corrupt the database or duplicate the project row.
  $a = Invoke-Pc $repo @('init','--indicator','AVRIG')
  Assert-True ($a.Exit -eq 0 -or $a.Exit -eq 3) 'a repeat init is either a no-op or an explicit refusal'
  if ($a.Exit -eq 3) { Assert-Match $a.Out 'import|durable|_plan\.sql' 'the refusal names the durable record it will not clobber' }
  Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM project;') 'exactly one project row after a repeat init'
  Assert-Equal 1 (& $SQL -noheader $db 'PRAGMA user_version;') 'version still 1 after a repeat init'
  Assert-Equal 'ok' (& $SQL -noheader $db 'PRAGMA integrity_check;') 'integrity after a repeat init'

  # isolate the foreign-indicator guard from the durable-record guard
  Remove-Item -Force $dump -ErrorAction SilentlyContinue
  $b = Invoke-Pc $repo @('init','--indicator','WEB')
  Assert-Equal 3 $b.Exit 'second indicator refused'
  Assert-Equal 'AVRIG' (& $SQL -noheader $db 'SELECT indicator FROM project;') 'project row unchanged'
  Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM project;') 'no second project row'

  # a newer or unknown user_version is refused rather than silently applied
  Remove-Item -Force $dump -ErrorAction SilentlyContinue
  $uo = (& $SQL -bail $db 'PRAGMA user_version=99;' 2>&1) -join "`n"
  Assert-Equal 0 $LASTEXITCODE "set user_version 99 : $uo"
  $c = Invoke-Pc $repo @('init','--indicator','AVRIG')
  Assert-Equal 3 $c.Exit 'unknown newer user_version refused'
  Assert-Equal 99 (& $SQL -noheader $db 'PRAGMA user_version;') 'refused init did not rewrite the version'
  Assert-Equal 1 (& $SQL -noheader $db "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='project';") 'refused init did not touch the schema'

  # an empty file at the database path is initialised, which is the recovery path
  $fresh = Join-Path $TMP 't18\fresh'
  New-FixtureRepo $fresh 0
  [IO.File]::WriteAllBytes((Join-Path $fresh 'plans\_plan.db'), [byte[]]@())
  $d = Invoke-Pc $fresh @('init','--indicator','AVRIG')
  Assert-Equal 0 $d.Exit 'empty database file is initialised'
  Assert-Equal 1 (& $SQL -noheader (Join-Path $fresh 'plans\_plan.db') 'PRAGMA user_version;') 'initialised to version 1'
}

# ---------------------------------------------------------------------------
# T19 The migration left nothing behind. Read only, against the candidate tree.
# ---------------------------------------------------------------------------

function Invoke-Case-T19 {
  Assert-True (Test-Path -LiteralPath $WT) "the tree under test exists : $WT"
  $plans = Join-Path $WT 'plans'
  $dump  = Join-Path $plans '_plan.sql'
  $rules = Join-Path $plans 'PLAN-RULES.md'

  # 1. the numbered facts left the document tree rather than being duplicated in it
  Assert-True (-not (Test-Path -LiteralPath (Join-Path $plans 'PLAN-INDEX.md'))) 'plans/PLAN-INDEX.md does not exist'

  # 2. the one remaining declaration site carries both keys
  Assert-True (Test-Path -LiteralPath $rules) 'plans/PLAN-RULES.md exists'
  $rulesText = [IO.File]::ReadAllText($rules)
  $fmMatch = [regex]::Match($rulesText, '(?s)\A\s*---\r?\n(?<fm>.*?)\r?\n---')
  Assert-True $fmMatch.Success 'plans/PLAN-RULES.md opens with a frontmatter block'
  $fm = $fmMatch.Groups['fm'].Value
  Assert-Match $fm '(?m)^project_indicator:\s*\S+' 'the frontmatter carries project_indicator'
  Assert-Match $fm '(?m)^indicator_status:\s*\S+' 'the frontmatter carries indicator_status'
  $indicator = ([regex]::Match($fm, '(?m)^project_indicator:\s*(?<v>[A-Za-z][A-Za-z0-9]*)\s*$')).Groups['v'].Value
  Assert-Match $indicator '^[A-Z][A-Z0-9]{1,9}$' 'the declared indicator matches the shape rule'

  # 3. the archive is tracked and the database is not, by a rule that names it
  Assert-True (Test-Path -LiteralPath $dump) 'plans/_plan.sql exists'
  $tracked = Invoke-Git $WT @('ls-files','--error-unmatch','--','plans/_plan.sql')
  Assert-Equal 0 $tracked.Exit 'plans/_plan.sql is tracked by git'
  $dbTracked = Invoke-Git $WT @('ls-files','--','plans/_plan.db')
  Assert-Equal '' $dbTracked.Out.Trim() 'plans/_plan.db is not tracked by git'
  $ign = Invoke-Git $WT @('check-ignore','-v','--','plans/_plan.db')
  Assert-Equal 0 $ign.Exit 'plans/_plan.db is ignored'
  Add-Log "T19 check-ignore : $($ign.Out)"
  Assert-Match $ign.Out '_plan\.db\*' 'the ignore rule names plans/_plan.db*'

  # 4. the committed dump rebuilds the four historical rows, and nothing else, in a
  #    scratch database. This is the goal the whole change rests on, so it is graded
  #    on the archive rather than on the live database.
  $scratch = Join-Path $TMP 't19\dump.db'
  New-Item -ItemType Directory -Force (Split-Path $scratch) | Out-Null
  Remove-Item -Force $scratch, "$scratch-wal", "$scratch-shm" -ErrorAction SilentlyContinue
  $load = (Get-Content -Raw -LiteralPath $dump | & $SQL -bail $scratch 2>&1) -join "`n"
  $loadExit = $LASTEXITCODE
  Assert-Equal 0 $loadExit "the committed dump applies to a scratch database : $load"

  Assert-Equal 4 ([int](& $SQL -noheader $scratch 'SELECT COUNT(*) FROM work_item;')) 'the ledger holds the four historical work items'
  Assert-Equal 6 ([int](& $SQL -noheader $scratch 'SELECT COUNT(*) FROM deferred_defect;')) 'the ledger holds the six deferred defects'
  Assert-Equal 0 ([int](& $SQL -noheader $scratch 'SELECT COUNT(*) FROM indicator_alias;')) 'this migration needed no indicator alias'
  Assert-Equal 1 ([int](& $SQL -noheader $scratch 'SELECT COUNT(*) FROM project;')) 'exactly one project row'
  Assert-Equal "$indicator" (& $SQL -noheader $scratch 'SELECT indicator FROM project;') 'the project row carries the declared indicator'
  Assert-Equal '1,2,3,4' (((& $SQL -noheader $scratch 'SELECT group_concat(number) FROM (SELECT number FROM work_item ORDER BY number);') -join '') -replace '\s','') 'the four rows are numbers 1 to 4 with no gap'

  # 5. every historical row still carries its own code, and a real status
  $vocab = "('" + ($script:StatusVocab -join "','") + "')"
  $badRows = (((& $SQL -noheader $scratch (
      'SELECT group_concat(number) FROM work_item WHERE ' +
      'claiming_branch IS NULL OR instr(claiming_branch, code || ''-'') = 0 ' +
      'OR plan_path IS NULL OR instr(plan_path, code || ''-'') = 0 ' +
      "OR ledger_status IS NULL OR ledger_status NOT IN $vocab;")) -join '') -replace '\s','')
  Assert-Equal '' $badRows 'every historical row carries its code in branch and plan path, and a vocabulary status'
  Assert-Equal 0 ([int](& $SQL -noheader $scratch (
      "SELECT COUNT(*) FROM work_item WHERE instr(claiming_branch, code || '-') = 0;"))) 'no row lost its code from the claiming branch'
  Assert-Equal 0 ([int](& $SQL -noheader $scratch (
      "SELECT COUNT(*) FROM work_item WHERE instr(plan_path, code || '-') = 0;"))) 'no row lost its code from the plan path'

  # 6. what the archive may and may not carry. Two machine values are there by design:
  #    actor_host and actor_user on every row are the audit trail, and deferred_defect
  #    keeps the words a finding was written with, so scrubbing a real path out of a
  #    real description would falsify the evidence. The project row is derived, so it
  #    holds no machine path, and the evidence itself is asserted positively.
  $dumpText = [IO.File]::ReadAllText($dump)

  Assert-Equal 0 ([int](& $SQL -noheader $scratch 'SELECT COUNT(*) FROM project WHERE repo_root IS NOT NULL;')) 'the project row carries no repo_root'
  $projectCells = ((& $SQL -noheader $scratch (
      "SELECT COALESCE(indicator,'')||'|'||COALESCE(project_key,'')||'|'||COALESCE(repo_root,'')||'|'||" +
      "CAST(frozen AS TEXT)||'|'||COALESCE(created_at,'') FROM project;")) -join "`n")
  Assert-True (-not ($projectCells -match '(?<![A-Za-z0-9])[A-Za-z]:[\\/]')) 'no column of project carries a drive letter'
  Assert-True (-not ($projectCells -match '(?i)[\\/]users[\\/]')) 'no column of project carries a Users path fragment'

  # the record keeps its evidence: the defect that names a real path still names it, so
  # a later cleanup that scrubs it is caught as a change rather than passing silently
  Assert-Equal 1 ([int](& $SQL -noheader $scratch (
      "SELECT COUNT(*) FROM deferred_defect WHERE found_during='AVRIG-00003' " +
      "AND instr(defect,'.opencode/agents') > 0;"))) 'the defect that names a real path still names it'

  # 7. the header is a promise the tool keeps: generated, not hand edited, and an
  #    export --check reads without writing
  Assert-Match $dumpText 'Generated by plan-code\.ps1 export from plans/_plan\.db\. Do not edit by hand' 'the header says the dump is generated and must not be hand edited'
  $sha = Get-Sha256 $dump
  $chk = Invoke-Export $WT -Check
  Assert-True ($chk.Exit -eq 0 -or $chk.Exit -eq 1) "export --check reports in sync or drift, never a configuration failure : exit $($chk.Exit)"
  Assert-Equal $sha (Get-Sha256 $dump) 'export --check left plans/_plan.sql byte identical'
}

# ---------------------------------------------------------------------------
# T20 The update subcommand: the writer the delivery stages were missing
# ---------------------------------------------------------------------------

function Invoke-Case-T20 {
  $repo = Join-Path $TMP 't20'
  New-FixtureRepo $repo 3 -SeedDb -ExportDump
  $db = Join-Path $repo 'plans\_plan.db'

  # The subject is the update subcommand, so its absence is BLOCKED, not a failure of
  # the contract and not a skip. The baseline is taken before the probe so the probe's
  # own event is counted.
  function Get-Count([string]$Query) { [int]((& $SQL -noheader $db $Query) -join '') }
  $otherDigestSql = "SELECT group_concat(code||'|'||state||'|'||COALESCE(ledger_status,'~'),';') FROM (SELECT * FROM work_item WHERE number <> 2 ORDER BY number);"
  $fullDigestSql  = "SELECT group_concat(code||'|'||state||'|'||COALESCE(ledger_status,'~')||'|'||COALESCE(candidate_tags,'~')||'|'||COALESCE(evidence_path,'~')||'|'||COALESCE(issue_number,'~')||'|'||COALESCE(issue_url,'~')||'|'||COALESCE(release_version,'~'),';') FROM (SELECT * FROM work_item ORDER BY number);"

  $ev0 = Get-Count 'SELECT COUNT(*) FROM allocation_event;'
  $digest0 = (& $SQL -noheader $db $otherDigestSql) -join ''

  $probe = Invoke-Pc $repo @('update','--code','AVRIG-00002','--status','testing')
  if ($probe.Exit -eq 3 -and $probe.Out -match 'unknown subcommand') {
    Add-Log "T20 BLOCKED : $($probe.Out)"
    return (Set-Blocked "the allocator has no update subcommand : $($probe.Out -replace '\s+', ' ')")
  }

  # 1. --status changes that row only, and writes exactly one event
  Assert-Equal 0 $probe.Exit 'update --status exits 0'
  Assert-Equal 'testing' (& $SQL -noheader $db 'SELECT ledger_status FROM work_item WHERE number=2;') 'ledger_status was written'
  Assert-Equal 1 (Get-Count "SELECT COUNT(*) FROM work_item WHERE ledger_status='testing';") 'the status changed on that row only'
  Assert-Equal $digest0 ((& $SQL -noheader $db $otherDigestSql) -join '') 'no other row was touched'
  Assert-Equal ($ev0 + 1) (Get-Count 'SELECT COUNT(*) FROM allocation_event;') 'exactly one event per update call'
  Assert-Equal 1 (Get-Count "SELECT COUNT(*) FROM allocation_event WHERE event='update' AND number=2;") 'the event is an update event on the updated row'
  Assert-Match (& $SQL -noheader $db 'SELECT COALESCE(detail,'''') FROM allocation_event WHERE event=''update'' ORDER BY id DESC LIMIT 1;') '(?i)status' 'the event detail names what changed'

  # the workhorse row for the rest of the case, so the candidate tag, evidence path,
  # issue, and version all belong to the same number
  $a = Invoke-Pc $repo @('assign','--title','update target','--role','Architect',
                         '--branch','feat/AVRIG-00004-update-target','--plan-path','plans/AVRIG-00004-2026-11-20-update-target.md')
  Assert-Equal 0 $a.Exit 'the target row is assigned'
  Assert-Equal 'AVRIG-00004' (Get-Code $a.Out) 'the target row is AVRIG-00004'
  New-PlanFile $repo 'plans/AVRIG-00004-2026-11-20-update-target.md' | Out-Null
  Assert-Equal 0 (Invoke-Export $repo).Exit 'export before the updates'
  Assert-Equal 0 (Invoke-Pc $repo @('verify','--strict')).Exit 'verify is clean before the updates'

  $ev = Get-Count 'SELECT COUNT(*) FROM allocation_event;'

  # 2. the six other allowlisted fields each write
  $c = Invoke-Pc $repo @('update','--code','AVRIG-00004','--candidate-tag','avrig/00004/rc.001')
  Assert-Equal 0 $c.Exit 'update --candidate-tag exits 0'
  Assert-Equal 'avrig/00004/rc.001' (& $SQL -noheader $db 'SELECT candidate_tags FROM work_item WHERE number=4;') 'candidate_tags was written'
  Assert-Equal ($ev + 1) (Get-Count 'SELECT COUNT(*) FROM allocation_event;') 'the candidate tag call wrote one event'

  $e = Invoke-Pc $repo @('update','--code','AVRIG-00004','--evidence','plans/evidence/AVRIG-00004/rc.001/')
  Assert-Equal 0 $e.Exit 'update --evidence exits 0'
  Assert-Equal 'plans/evidence/AVRIG-00004/rc.001/' (& $SQL -noheader $db 'SELECT evidence_path FROM work_item WHERE number=4;') 'evidence_path was written'

  $i = Invoke-Pc $repo @('update','--code','AVRIG-00004','--issue','6')
  Assert-Equal 0 $i.Exit 'update --issue exits 0'
  Assert-Equal 6 (Get-Count 'SELECT issue_number FROM work_item WHERE number=4;') 'issue_number was written'
  $url = (& $SQL -noheader $db "SELECT COALESCE(issue_url,'') FROM work_item WHERE number=4;") -join ''
  Add-Log "T20 issue_url after --issue 6 : [$url]"
  Assert-True ([string]::IsNullOrEmpty($url) -or $url -match '/issues/6$') "issue_url is either derived from --issue or left empty : got [$url]"

  # nothing invents a version: the field stays empty until deployment writes it
  Assert-Equal '' ((& $SQL -noheader $db "SELECT COALESCE(release_version,'') FROM work_item WHERE number=4;") -join '') 'release_version is not invented by the other fields'

  $r = Invoke-Pc $repo @('update','--code','AVRIG-00004','--release-version','9.9.9')
  Assert-Equal 0 $r.Exit 'update --release-version is accepted rather than refused'
  Assert-Equal '9.9.9' (& $SQL -noheader $db 'SELECT release_version FROM work_item WHERE number=4;') 'release_version was written verbatim'

  # the seventh field: the pointer is repairable, so a row that rotted can be fixed
  # rather than re-keyed. Its shape rules are graded in T21; here only that it writes.
  $repair = 'plans/AVRIG-00004-2026-11-20-renamed.md'
  New-PlanFile $repo $repair | Out-Null
  $p = Invoke-Pc $repo @('update','--code','AVRIG-00004','--plan-path',$repair)
  Assert-Equal 0 $p.Exit 'update --plan-path exits 0'
  Assert-Equal $repair (& $SQL -noheader $db 'SELECT plan_path FROM work_item WHERE number=4;') 'plan_path was written'

  $events = Get-Count 'SELECT COUNT(*) FROM allocation_event;'
  Assert-Equal ($ev + 5) $events 'five allowlisted calls wrote five events and no more'
  Assert-Equal 1 (Get-Count "SELECT COUNT(*) FROM allocation_event WHERE event='update' AND number=2;") 'the only other update event belongs to the status call'
  Assert-Equal 0 (Get-Count "SELECT COUNT(*) FROM allocation_event WHERE event='update' AND number NOT IN (2,4);") 'no update event was filed against a row that was not updated'

  # 3. the refusals. Each proves exit 3, and nothing at all is written.
  Assert-Equal 0 (Invoke-Pc $repo @('void','--code','AVRIG-00003','--reason','probe: voided rows are not updateable')).Exit 'void the row used for the voided refusal'
  $rowsBefore = Get-Count 'SELECT COUNT(*) FROM work_item;'
  $evBefore   = Get-Count 'SELECT COUNT(*) FROM allocation_event;'
  $digestBefore = (& $SQL -noheader $db $fullDigestSql) -join ''

  $refusals = @(
    @{ Id='an unknown code';                    Arg=@('--code','AVRIG-09999','--status','testing') }
    @{ Id='setting indicator';                  Arg=@('--code','AVRIG-00004','--indicator','WXYZ') }
    @{ Id='setting number';                     Arg=@('--code','AVRIG-00004','--number','9') }
    @{ Id='setting state';                      Arg=@('--code','AVRIG-00004','--state','voided') }
    @{ Id='setting assigned_at';                Arg=@('--code','AVRIG-00004','--assigned-at','2026-11-20T00:00:00.000Z') }
    @{ Id='setting committed_at';               Arg=@('--code','AVRIG-00004','--committed-at','2026-11-20T00:00:00.000Z') }
    @{ Id='setting voided_at';                  Arg=@('--code','AVRIG-00004','--voided-at','2026-11-20T00:00:00.000Z') }
    @{ Id='setting voided_reason';              Arg=@('--code','AVRIG-00004','--voided-reason','x') }
    @{ Id='updating a row whose state is voided'; Arg=@('--code','AVRIG-00003','--status','testing') }
  )
  foreach ($c in $refusals) {
    $x = Invoke-Pc $repo $c.Arg
    Assert-Equal 3 $x.Exit "$($c.Id) is refused with exit 3"
    Assert-True ($x.Out.Trim().Length -gt 0) "$($c.Id) refusal says something rather than failing silently"
    Assert-Equal $rowsBefore (Get-Count 'SELECT COUNT(*) FROM work_item;') "$($c.Id) wrote no row"
    Assert-Equal $evBefore (Get-Count 'SELECT COUNT(*) FROM allocation_event;') "$($c.Id) wrote no event"
    Assert-Equal $digestBefore ((& $SQL -noheader $db $fullDigestSql) -join '') "$($c.Id) changed no column of any row"
  }

  # An immutable column cannot be reached even when a legal field is named in the same
  # call. The refusal style is not graded here, only that the columns did not move:
  # a parser that quietly drops --indicator or --state is tolerable, one that writes
  # them is not.
  $mix = Invoke-Pc $repo @('update','--code','AVRIG-00004','--status','passed',
                           '--indicator','WXYZ','--state','voided')
  Add-Log "T20 mixed immutable probe exit=$($mix.Exit) : $($mix.Out)"
  Assert-True ($mix.Exit -eq 0 -or $mix.Exit -eq 3) 'a call naming an immutable field either runs or refuses, never fails another way'
  Assert-Equal 'AVRIG' (& $SQL -noheader $db 'SELECT indicator FROM work_item WHERE number=4;') 'no flag reached the indicator column'
  Assert-Equal 4 (Get-Count 'SELECT number FROM work_item WHERE number=4;') 'no flag reached the number column'
  Assert-Equal 'committed' (& $SQL -noheader $db 'SELECT state FROM work_item WHERE number=4;') 'no flag reached the state column'

  # 4. hostile strings land unchanged and leave the table intact. A value that lands and
  #    an exit code that says "refused" cannot both be true, so the write is graded with
  #    the exit code a caller branches on.
  $hostiles = @(
    @{ Id='a quote, a semicolon and a SQL comment'; Value="plans/ev'; DROP TABLE work_item; --/x" }
    @{ Id='a quote, a comment and a newline';       Value="plans/ev'; DROP TABLE work_item; --/x`nsecond line" }
  )
  foreach ($c in $hostiles) {
    $h = Invoke-Pc $repo @('update','--code','AVRIG-00004','--evidence',$c.Value)
    Add-Log "T20 hostile [$($c.Id)] exit=$($h.Exit) : $($h.Out)"
    Assert-Equal 0 $h.Exit "$($c.Id) is accepted, because the value must not be stored and reported as a refusal at the same time"
    Assert-Equal $c.Value ((((& $SQL -noheader $db 'SELECT evidence_path FROM work_item WHERE number=4;') -join "`n").TrimEnd())) "$($c.Id) lands verbatim"
  }
  Assert-Equal 5 (Get-Count "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';") 'all five tables survive the hostile strings'
  Assert-Equal 4 (Get-Count 'SELECT COUNT(*) FROM work_item;') 'the hostile strings dropped no row'
  Assert-Equal 'ok' (& $SQL -noheader $db 'PRAGMA integrity_check;') 'integrity after the hostile strings'

  # 5. the drift gate: update without export is caught, export resolves it
  $v1 = Invoke-Pc $repo @('verify','--strict')
  Assert-Equal 1 $v1.Exit 'an update without export is drift, so strict verify fails'
  Assert-Match $v1.Out 'drift:' 'the finding is labelled drift'
  Assert-Equal 0 (Invoke-Export $repo).Exit 'export after the updates'
  Assert-True (@(Select-String -Path (Join-Path $repo 'plans\_plan.sql') -Pattern 'avrig/00004/rc.001' -SimpleMatch).Count -ge 1) 'the exported dump carries the candidate tag'
  Assert-Equal 0 (Invoke-Pc $repo @('verify','--strict')).Exit 'update then export then verify --strict is clean'
}


# ---------------------------------------------------------------------------
# T21 Verify checks the plan pointer rather than trusting it
# ---------------------------------------------------------------------------

function Invoke-Case-T21 {
  $repo = Join-Path $TMP 't21'
  New-FixtureRepo $repo 3 -SeedDb -ExportDump
  $db = Join-Path $repo 'plans\_plan.db'

  function Get-Count([string]$Query) { [int]((& $SQL -noheader $db $Query) -join '') }
  $sqlErr = $null
  $digestSql = "SELECT group_concat(code||'|'||state||'|'||COALESCE(plan_path,'~'),';') FROM (SELECT * FROM work_item ORDER BY number);"

  # 1. the baseline: every committed row names a real file, which is the shape a project
  #    reaches at approval, so a pointer that resolves is not drift
  Assert-Equal 0 (Invoke-Pc $repo @('verify','--strict')).Exit 'a ledger whose pointers resolve is clean'

  # 2. a committed row naming a file that is not there. The writer refuses to create this
  #    state, which is the point of 7 below, so the probe writes it where only SQL can.
  $gone = 'plans/AVRIG-00002-2026-11-20-gone.md'
  $sqlErr = (& $SQL -bail $db "UPDATE work_item SET plan_path='$gone' WHERE number=2;" 2>&1) -join ' '
  Assert-Equal 0 $LASTEXITCODE "the probe row now names a file that is not there : $sqlErr"

  $v = Invoke-Pc $repo @('verify','--strict')
  Assert-Equal 1 $v.Exit 'strict fails on a committed row pointing at nothing'
  Assert-Match $v.Out 'drift:' 'the finding is labelled drift'
  Assert-Match $v.Out 'AVRIG-00002' 'the finding names the row'
  Assert-Match $v.Out ([regex]::Escape($gone)) 'the finding names the path'
  $plain = Invoke-Pc $repo @('verify')
  Assert-Equal 0 $plain.Exit 'plain verify reports without failing'
  Assert-Match $plain.Out ([regex]::Escape($gone)) 'plain verify prints the same finding'

  # 3. the repair the tool sanctions: a pointer is fixed in place, not by re-keying the row
  $fixed = 'plans/AVRIG-00002-2026-11-20-fixed.md'
  New-PlanFile $repo $fixed | Out-Null
  $evBefore = Get-Count 'SELECT COUNT(*) FROM allocation_event;'
  $rep = Invoke-Pc $repo @('update','--code','AVRIG-00002','--plan-path',$fixed)
  Assert-Equal 0 $rep.Exit 'update --plan-path repairs the row'
  Assert-Equal $fixed (& $SQL -noheader $db 'SELECT plan_path FROM work_item WHERE number=2;') 'the repaired pointer is stored'
  Assert-Equal ($evBefore + 1) (Get-Count 'SELECT COUNT(*) FROM allocation_event;') 'the repair writes exactly one event'
  Assert-Match (& $SQL -noheader $db "SELECT COALESCE(detail,'') FROM allocation_event ORDER BY id DESC LIMIT 1;") 'plan_path' 'the event detail names the field that changed'
  Assert-Equal 0 (Invoke-Export $repo).Exit 'export after the repair'
  Assert-Equal 0 (Invoke-Pc $repo @('verify','--strict')).Exit 'the repair clears the drift'

  # 4. a committed row with no pointer at all is its own finding rather than a silent pass
  $sqlErr = (& $SQL -bail $db 'UPDATE work_item SET plan_path=NULL WHERE number=3;' 2>&1) -join ' '
  Assert-Equal 0 $LASTEXITCODE "the second probe row now holds no pointer : $sqlErr"
  $e = Invoke-Pc $repo @('verify','--strict')
  Assert-Equal 1 $e.Exit 'strict fails on a committed row with no pointer'
  Assert-Match $e.Out '(?i)no plan_path' 'the empty pointer has its own message'
  Assert-Match $e.Out 'AVRIG-00003' 'the empty pointer names the row'

  # 5. the check covers committed rows, so a voided row is exempt. Voiding the probe row
  #    is therefore the resolution that needs no file, and the finding goes away with it.
  Assert-Equal 0 (Invoke-Pc $repo @('void','--code','AVRIG-00003','--reason','probe: the pointer check covers committed rows')).Exit 'void the row with no pointer'
  Assert-Equal 0 (Invoke-Export $repo).Exit 'export after the void'
  $vd = Invoke-Pc $repo @('verify','--strict')
  Assert-Equal 0 $vd.Exit 'a voided row is exempt from the pointer check'
  Assert-True (-not ($vd.Out -match 'AVRIG-00003')) 'the voided row is not reported'
  Assert-Equal '' ([string](& $SQL -noheader $db "SELECT COALESCE(plan_path,'') FROM work_item WHERE number=3;")) 'the voided row keeps its empty pointer, so the exemption is what passed it'

  # 6. stage 16 archives the plan under plans/done/, and the row follows it there
  $arch = 'plans/done/AVRIG-00001-2026-11-20-archived.md'
  New-PlanFile $repo $arch | Out-Null
  Assert-Equal 0 (Invoke-Pc $repo @('update','--code','AVRIG-00001','--plan-path',$arch)).Exit 'a path under plans/done/ is accepted'
  Assert-Equal 0 (Invoke-Export $repo).Exit 'export after the archive'
  Assert-Equal 0 (Invoke-Pc $repo @('verify','--strict')).Exit 'the archived pointer resolves'

  # 7. the guard. Each refusal proves exit 3 and that nothing at all was written.
  $rowsBefore   = Get-Count 'SELECT COUNT(*) FROM work_item;'
  $evBefore2    = Get-Count 'SELECT COUNT(*) FROM allocation_event;'
  $digestBefore = (& $SQL -noheader $db $digestSql) -join ''

  $refusals = @(
    @{ Id='an absolute path';        Arg=@('--code','AVRIG-00002','--plan-path','C:\tmp\AVRIG-00002-2026-11-20-x.md') }
    @{ Id='a path outside plans/';   Arg=@('--code','AVRIG-00002','--plan-path','docs/AVRIG-00002-2026-11-20-x.md') }
    @{ Id="another row's code";      Arg=@('--code','AVRIG-00002','--plan-path','plans/AVRIG-00005-2026-11-20-x.md') }
    @{ Id='no file behind the path'; Arg=@('--code','AVRIG-00002','--plan-path','plans/AVRIG-00002-2026-11-20-absent.md') }
  )
  foreach ($c in $refusals) {
    $x = Invoke-Pc $repo $c.Arg
    Assert-Equal 3 $x.Exit "$($c.Id) is refused with exit 3"
    Assert-True ($x.Out.Trim().Length -gt 0) "$($c.Id) refusal says something rather than failing silently"
    Assert-Equal $rowsBefore (Get-Count 'SELECT COUNT(*) FROM work_item;') "$($c.Id) wrote no row"
    Assert-Equal $evBefore2 (Get-Count 'SELECT COUNT(*) FROM allocation_event;') "$($c.Id) wrote no event"
    Assert-Equal $digestBefore ((& $SQL -noheader $db $digestSql) -join '') "$($c.Id) changed no column of any row"
  }

  # 8. the code has to be followed by the hyphen that the branch rule and T19 both demand,
  #    so a file that exists is not enough on its own. Graded last, because a tool that
  #    accepts it rewrites the pointer and there is nothing after this to disturb.
  $bare = 'plans/AVRIG-00002.md'
  New-PlanFile $repo $bare | Out-Null
  $b = Invoke-Pc $repo @('update','--code','AVRIG-00002','--plan-path',$bare)
  Add-Log "T21 bare basename probe exit=$($b.Exit) : $($b.Out)"
  Assert-Equal 3 $b.Exit 'a basename carrying the code with no hyphen after it is refused'
  Assert-Equal $digestBefore ((& $SQL -noheader $db $digestSql) -join '') 'the bare basename changed no column of any row'
}

# ---------------------------------------------------------------------------
# Case registry. Execution order follows the gate table in the plan: schema
# first, then single process behaviour, then the migration's leftovers, then
# contention on a clean fixture, then union and rebuild, durability, dump
# determinism, environment edges, runbook, and the update writer last because
# its subject may still be in flight.
# ---------------------------------------------------------------------------

$Cases = @{
  T01 = { Invoke-Case-T01 }
  T02 = { Invoke-Case-T02 }
  T03 = { Invoke-Case-T03 }
  T04 = { Invoke-Case-T04 }
  T05 = { Invoke-Case-T05 }
  T06 = { Invoke-Case-T06 }
  T07 = { Invoke-Case-T07 }
  T08 = { Invoke-Case-T08 }
  T09 = { Invoke-Case-T09 }
  T10 = { Invoke-Case-T10 }
  T11 = { Invoke-Case-T11 }
  T12 = { Invoke-Case-T12 }
  T13 = { Invoke-Case-T13 }
  T14 = { Invoke-Case-T14 }
  T15 = { Invoke-Case-T15 }
  T16 = { Invoke-Case-T16 }
  T17 = { Invoke-Case-T17 }
  T18 = { Invoke-Case-T18 }
  T19 = { Invoke-Case-T19 }
  T20 = { Invoke-Case-T20 }
  T21 = { Invoke-Case-T21 }
}

$ExecutionOrder = @('T01','T02','T12','T13','T17','T18','T19','T03','T04','T05','T08',
                    'T06','T07','T09','T10','T11','T15','T16','T14','T20','T21')
$Case = @($Case | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$unknown = @($Case | Where-Object { $ExecutionOrder -notcontains $_ })
if ($unknown.Count -gt 0) { throw "unknown case(s): $($unknown -join ', ')" }
$Selected = @($ExecutionOrder | Where-Object { $Case -contains $_ })

# ---------------------------------------------------------------------------
# Identity. A run against a working tree is recorded as such and is not evidence.
# ---------------------------------------------------------------------------

$projGit = Invoke-Git $Project @('rev-parse','HEAD')
$SHA = if ($projGit.Exit -eq 0) { $projGit.Out.Trim() } else { '(not a git checkout)' }
$toolGit = Invoke-Git $TOOL @('rev-parse','HEAD')
$TSHA = if ($toolGit.Exit -eq 0) { $toolGit.Out.Trim() } else { '(not a git checkout)' }
$dirty = Invoke-Git $TOOL @('status','--porcelain','--','shared/skills/plan-code')
$dirtyText = $dirty.Out.Trim()

if ($Tag) {
  $resolved = Invoke-Git $Project @('rev-parse', "$Tag^{commit}")
  if ($resolved.Exit -eq 0) { $SHA = $resolved.Out.Trim() }
  else { Write-Host "WARNING: -Tag $Tag does not resolve in $Project; the run is not tagged evidence." }
}
$TagText = if ($Tag) { $Tag } else { '(none)' }

$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$EvidenceDir = ''
if ($Out) {
  $EvidenceDir = (New-Item -ItemType Directory -Force -Path $Out).FullName
  New-Item -ItemType Directory -Force (Join-Path $EvidenceDir 'logs') | Out-Null
}

$PhaseResults = [System.Collections.Generic.List[string]]::new()

Write-Host ''
Write-Host "Test-Allocation.ps1  project=$Project"
Write-Host "tag=$TagText sha=$SHA tsha=$TSHA"
if ($dirtyText) { Write-Host "tool checkouts under test are modified (not candidate evidence):`n$dirtyText" }
Write-Host "scratch=$TMP  keep=$([bool]$Keep)  cases=$($Selected -join ',')"
if (-not $Tag) { Write-Host 'NOTE: no -Tag given, so this is a working tree run and not candidate evidence.' }
Write-Host ''

# ---------------------------------------------------------------------------
# Preflight. A missing subject is reported per case as a failing case, with the
# reason, rather than as a silent skip.
# ---------------------------------------------------------------------------

$blockers = @()
if (-not (Test-Path -LiteralPath $PC))  { $blockers += "the allocator does not exist: $PC" }
if (-not (Test-Path -LiteralPath $DDL)) { $blockers += "the schema does not exist: $DDL" }
if (-not (Test-Path -LiteralPath $PW))  { $blockers += "pwsh does not exist at $PW" }
if (-not (Test-Path -LiteralPath $SQL)) { $blockers += "sqlite3 does not exist at $SQL and is not on PATH" }
if (-not (Test-Path -LiteralPath $Project)) { $blockers += "the project path does not exist: $Project" }

$PassCount = 0
$FailCount = 0
$BlockedCount = 0

if ($blockers.Count -gt 0) {
  foreach ($b in $blockers) { Write-Host "BLOCKED: $b" }
  foreach ($id in $Selected) {
    $line = "$id FAIL 0/0 tag=$TagText sha=$SHA tsha=$TSHA reason=BLOCKED $($blockers[0])"
    Write-Host $line
    $PhaseResults.Add($line)
    $FailCount++
  }
} else {
  New-Item -ItemType Directory -Force $TMP | Out-Null

  foreach ($id in $Selected) {
    $script:Total = 0
    $script:Passed = 0
    $script:Blocked = $null
    $script:CaseLog = [System.Collections.Generic.List[string]]::new()
    Add-Log "===== $id started $(Get-Date -Format o) ====="
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $failure = $null

    try {
      & $Cases[$id]
    } catch {
      $failure = $_.Exception.Message
      Add-Log "!!!!! $id threw : $failure"
      if ($_.ScriptStackTrace) { Add-Log $_.ScriptStackTrace }
    }

    $sw.Stop()
    Add-Log ("===== $id finished in {0:N1}s : {1}/{2} assertions =====" -f $sw.Elapsed.TotalSeconds, $script:Passed, $script:Total)

    if ($failure) {
      $reason = (($failure -replace '\s+', ' ').Trim())
      if ($reason.Length -gt 300) { $reason = $reason.Substring(0, 300) }
      $line = "$id FAIL $($script:Passed)/$($script:Total) tag=$TagText sha=$SHA tsha=$TSHA reason=$reason"
      $FailCount++
    } elseif ($script:Blocked) {
      # BLOCKED is not a pass: the case did not execute its subject, so its absence
      # fails the run rather than turning a missing subject into a green result.
      $reason = (("$($script:Blocked)" -replace '\s+', ' ').Trim())
      if ($reason.Length -gt 300) { $reason = $reason.Substring(0, 300) }
      $line = "$id BLOCKED $($script:Passed)/$($script:Total) tag=$TagText sha=$SHA tsha=$TSHA reason=$reason"
      $BlockedCount++
    } else {
      $line = "$id PASS $($script:Passed)/$($script:Total) tag=$TagText sha=$SHA tsha=$TSHA"
      $PassCount++
    }

    Write-Host $line
    $PhaseResults.Add($line)

    if ($EvidenceDir) {
      $logPath = Join-Path $EvidenceDir "logs\$id.log"
      [IO.File]::WriteAllText($logPath, ($script:CaseLog -join "`r`n"), [Text.UTF8Encoding]::new($false))
    }
  }
}

$exit = if ($FailCount -gt 0 -or $BlockedCount -gt 0) { 1 } else { 0 }
$rollup = "ROLLUP $PassCount/$($Selected.Count) PASS exit=$exit"
if ($BlockedCount -gt 0) { $rollup += " blocked=$BlockedCount" }
if ($FailCount -gt 0) { $rollup += " failed=$FailCount" }
Write-Host ''
Write-Host $rollup

if ($EvidenceDir) {
  $envObj = [ordered]@{
    ps        = "$($PSVersionTable.PSVersion)"
    sqlite3   = ((& $SQL --version) -join '')
    tag       = $Tag
    sha       = $SHA
    tsha      = $TSHA
    tool_status = $dirtyText
    project   = $Project
    started   = $Stamp
  }
  [IO.File]::WriteAllText((Join-Path $EvidenceDir 'env.json'),
    ($envObj | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))

  $md = @(
    '# Test-Allocation.ps1 results',
    '',
    "tag: $TagText",
    "sha: $SHA",
    "tsha: $TSHA",
    "project: $Project",
    "scratch: $TMP",
    "started: $Stamp",
    '',
    'One line per case. The log is the record; this summary only points at it.',
    ''
  ) + $PhaseResults + @('', $rollup, '')
  [IO.File]::WriteAllText((Join-Path $EvidenceDir 'RESULTS.md'), ($md -join "`r`n"), [Text.UTF8Encoding]::new($false))
  Write-Host "evidence: $EvidenceDir"
}

if ($Keep) {
  Write-Host "scratch retained: $TMP"
} else {
  Remove-Item -Recurse -Force $TMP -ErrorAction SilentlyContinue
}

exit $exit

