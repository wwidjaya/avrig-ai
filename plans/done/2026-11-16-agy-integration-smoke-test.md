---
title: "Plan: agy Integration Smoke Test"
type: task-plan
status: completed
created: 2026-11-16
author: avrig-ai
tags:
  - plan
  - integration-test
  - agy
---

# Plan: agy Integration Smoke Test

## Objective

Verify the agy delegation loop with a harmless, user-directed file creation after agy asks for the exact content and waits for the user's answer.

## Scope and safeguards

- Read this plan and repository instructions only during the initial agy call.
- Do not modify files, run tests, install dependencies, access the network, or inspect secrets during the initial call.
- After the user answers agy's question, create only `plans/agy-integration-smoke-result.md` with the agreed content.
- Do not modify application source, project configuration, or other plans.

## Phase 1: Review and ask

Assignee: primary

Have agy inspect this plan, report any questions needed to execute it, and stop. It must not make changes at this stage. Its question should ask the user for the exact short text to place in the result file.

## Phase 2: Execute after user answer

Assignee: primary

After the user supplies the text, have agy create `plans/agy-integration-smoke-result.md` containing exactly that text and a final newline. Preserve all unrelated work. Report the file path and contents. Do not run tests.

## Completion

Once phase 2 is complete, mark this plan completed and move it to `plans/done/`.
