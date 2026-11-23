-- 001-plan.sql
-- Schema for plans/_plan.db, the per project plan code allocation ledger.
-- Plan AVRIG-00004, plan code allocation via a SQLite allocation ledger.
-- Version marker is PRAGMA user_version = 1.
-- Amended under AVRIG-00004 before any release, so this is version 1 revised
-- rather than a 002-plan.sql migration.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
PRAGMA user_version = 1;

CREATE TABLE IF NOT EXISTS project (
  indicator      TEXT PRIMARY KEY
                 CHECK (length(indicator) BETWEEN 2 AND 10
                        AND substr(indicator,1,1) GLOB '[A-Z]'
                        AND indicator NOT GLOB '*[^A-Z0-9]*'),
  project_key    TEXT NOT NULL UNIQUE,
  repo_root      TEXT,
  frozen         INTEGER NOT NULL DEFAULT 0 CHECK (frozen IN (0,1)),
  created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS work_item (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  indicator        TEXT    NOT NULL REFERENCES project(indicator) ON DELETE RESTRICT,
  number           INTEGER NOT NULL CHECK (number BETWEEN 1 AND 99999),
  code             TEXT    GENERATED ALWAYS AS (indicator || '-' || printf('%05d', number)) STORED,
  title            TEXT    NOT NULL CHECK (length(trim(title)) > 0),
  created_on       TEXT    CHECK (created_on IS NULL OR created_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  repos            TEXT,
  state            TEXT    NOT NULL CHECK (state IN ('committed','voided')),
  owner_role       TEXT    NOT NULL CHECK (length(trim(owner_role)) > 0),
  actor_host       TEXT    NOT NULL CHECK (length(trim(actor_host)) > 0),
  actor_user       TEXT    NOT NULL CHECK (length(trim(actor_user)) > 0),
  claiming_branch  TEXT,
  plan_path        TEXT,
  issue_number     INTEGER,
  issue_url        TEXT,
  evidence_path    TEXT,
  ledger_status    TEXT    CHECK (ledger_status IS NULL OR ledger_status IN
                     ('draft','under-review','awaiting-approval','approved','in-progress',
                      'testing','passed','release-version-decided','merged','deployed',
                      'released','abandoned')),
  candidate_tags   TEXT,
  release_version  TEXT,
  assigned_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  committed_at     TEXT,
  voided_at        TEXT,
  voided_reason    TEXT,
  CONSTRAINT uq_work_item_number UNIQUE (indicator, number),
  CONSTRAINT uq_work_item_code   UNIQUE (code),
  CONSTRAINT ck_committed_branch CHECK (state <> 'committed' OR claiming_branch IS NOT NULL),
  CONSTRAINT ck_committed_at     CHECK (state <> 'committed' OR committed_at IS NOT NULL),
  CONSTRAINT ck_voided_reason    CHECK (state <> 'voided'    OR voided_reason IS NOT NULL),
  CONSTRAINT ck_branch_carries_code
    CHECK (claiming_branch IS NULL
           OR instr(claiming_branch, indicator || '-' || printf('%05d', number) || '-') > 0)
);

CREATE INDEX IF NOT EXISTS ix_work_item_state ON work_item (state);

CREATE TABLE IF NOT EXISTS allocation_event (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  indicator  TEXT NOT NULL,
  number     INTEGER NOT NULL,
  event      TEXT NOT NULL CHECK (event IN ('assign','void','import','verify','update')),
  actor_role TEXT NOT NULL,
  actor_host TEXT NOT NULL,
  actor_user TEXT NOT NULL,
  detail     TEXT,
  at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS deferred_defect (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  found_during TEXT    NOT NULL CHECK (length(trim(found_during)) > 0),
  defect       TEXT    NOT NULL CHECK (length(trim(defect)) > 0),
  evidence     TEXT,
  at           TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
-- found_during holds a work item code such as AVRIG-00001 as text rather than as a
-- foreign key, because work_item.code is a generated column and SQLite cannot point
-- a foreign key at one. Do not "fix" this into a REFERENCES clause.

CREATE TABLE IF NOT EXISTS indicator_alias (
  old_code    TEXT PRIMARY KEY,
  new_code    TEXT NOT NULL,
  migrated_on TEXT
);

CREATE TRIGGER IF NOT EXISTS tr_allocation_event_no_update
BEFORE UPDATE ON allocation_event
BEGIN SELECT RAISE(ABORT, 'allocation_event is append-only'); END;

CREATE TRIGGER IF NOT EXISTS tr_allocation_event_no_delete
BEFORE DELETE ON allocation_event
BEGIN SELECT RAISE(ABORT, 'allocation_event is append-only'); END;

CREATE TRIGGER IF NOT EXISTS tr_work_item_no_delete
BEFORE DELETE ON work_item
BEGIN SELECT RAISE(ABORT, 'work_item rows are permanent; void the row instead of deleting it'); END;

CREATE TRIGGER IF NOT EXISTS tr_work_item_no_rekey
BEFORE UPDATE OF indicator, number ON work_item
BEGIN SELECT RAISE(ABORT, 'indicator and number are immutable once written'); END;
