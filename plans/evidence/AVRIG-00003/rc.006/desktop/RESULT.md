RESULT: tag avrig/00003/rc.006 | commit e006c0dc10b551f93abbb401b4caf6218a6517d7 | CLI agent-desktop 1.3.1 (envelope schema 2.6, not a product version) | verdict PASS | 74 of 74 checks passed | 54 of 54 mandatory passed | 0 blocked | evidence plans/evidence/AVRIG-00003/rc.006/desktop/ | scored against definition sha256 46EC68BE... at 09:50, with a post-run concurrent edit of that untracked file recorded in Post-run drift

# RESULT, AVRIG-00003, candidate avrig/00003/rc.006

## What was tested

The candidate commit only, resolved with `git rev-parse "avrig/00003/rc.006^{commit}"` and equal to
e006c0dc10b551f93abbb401b4caf6218a6517d7, in the worktree
D:\Cloud\OneDrive\AI\Agentic\AVRIG-00003\avrig-ai on branch
chore/AVRIG-00003-agent-desktop-uat-tooling, with `git status --porcelain` empty at run open and at
run close. The artifact under test is the installed CLI plus the tester definition, not a product
binary: this plan changes no product source, and the live loop targets Notepad instead of a built app.

## The three-way definition check

  live at 09:50 .opencode/agents/tester.md     sha256 46EC68BE1D15F03CB2EBF0B921510BC8D389BEF0D08CED8D67F96C85771703D2
  pinned  plans/evidence/AVRIG-00003/tester.md.tested
                                              sha256 46EC68BE1D15F03CB2EBF0B921510BC8D389BEF0D08CED8D67F96C85771703D2
  manifest files[0].Sha256 and amendments[-1].sha256_after
                                              sha256 46EC68BE1D15F03CB2EBF0B921510BC8D389BEF0D08CED8D67F96C85771703D2
  live versus pinned text diff                empty, 0 differing lines
  live size                                   27513 bytes, 248 lines, matching the manifest Bytes and Lines
  backup .bak-20261120-062939                 present, sha256 ED5581F4...4F56, matches BackupSha256
  manifest rows marked MISSING                0

Held at 09:50:05, the reading every G and H row is scored on. Evidence:
logs/G13-manifest-readback.txt.

## Post-run drift, recorded rather than tidied

The definition moved after this run finished, and a reader must not be told otherwise.

  at 09:50:05   live 46EC68BE... = pinned = manifest = amendments[-1].sha256_after, 0 differing lines
  at 09:56      live 1E52D9ACF121AF4C0594239822C18B8CB3F19616102C628820AF3BC593B24C3D
                pinned 46EC68BE..., 2 differing lines, 27556 bytes, 248 lines
                file mtime 2026-11-20 09:53:50

One line changed, in Responsibilities item 1: the plan indicator source moved from
`plans/PLAN-INDEX.md` to `project_indicator:` in the frontmatter of `plans/PLAN-RULES.md`. That is
not this work item's scope, it is not in the candidate tag, and this session wrote no byte of the
file. The file is untracked in the Agentic repository, so git attributes it to nobody.

What this means, precisely:

  every G, H and N row was scored against the 46EC68BE bytes, and every one of those logs was
  written before 09:53:50, so the run's PASS set belongs to those bytes
  H4's carve-out was computed at 09:51:48 against the 46EC68BE bytes and remains the record for
  this run. The later edit lands inside item 1's already-carved-out line, so it would not change
  H4's shape even if it were in scope
  the current live bytes have NOT been scored by this run, and this run claims nothing about them
  the file was not reverted. Reverting another writer's work to make a hash line read clean would
  be worse than reporting the drift

Recovery for the next run: re-pin `tester.md.tested` and the manifest `Sha256` once the concurrent
edit settles, then re-score G13. G13's PASS belongs to the 09:50 reading and to no later one.

## Discipline observed

  no --headed run, for anything. The F7 recovery invitation was declined by contract
  every secret-shaped value travelled on stdin through agent-desktop.cmd, never the .ps1 shim, and
  never in an argument list. delivered_verified decided no row
  the only argument-list literal is the declared non-secret probe uat-probe-0003 in F7
  the desktop was left clean: logs/FINAL-list-apps.json lists no Notepad.exe and
  logs/FINAL-list-windows.txt is empty
  nothing was committed, staged, tagged, merged or pushed

## THE FINDING THAT MATTERS: the silent ref redirect reproduced (E2)

rc.005 measured a loud refusal here and recorded the identity clause as not triggered. This run
reproduced the redirect the row exists for, twice, and it is the one result that differs in kind from
the previous candidate.

  capture    snapshot s140zy7gstwrt6, ref @s140zy7gstwrt6:e5, the Close Tab button of the SELECTED tab
  act 1      click that ref -> ok true, InvokePattern.Invoke succeeded. The selected tab closed and
             the addressed node ceased to exist; ref_count fell 27 to 26
  fresh      snapshot s1zuzkr15qwej7 between the acts: one tab left, its Close Tab is e4, a different ref
  act 2      click the SAME ref -> ok true AGAIN. No STALE_REF, no AMBIGUOUS_TARGET, no warning of any
             kind. It resolved onto the surviving tab's identical Close Tab and closed the remaining
             tab and the window with it

The identity read is the assertion, and it was performed between the acts: ref_id differs (e5 versus
e4), the owning tab node differs, and name and owning window id are identical, which is exactly why
the redirect is invisible in the envelope. Evidence: logs/E2-identity-read.txt, and the envelope
chain E2b-snapshot-two-tabs, E2b-act1, E2b-snapshot-after-removal, E2b-act2-redirect.

The hazard is stated plainly: an agent that trusts ok true believes the second act re-invoked the
control it captured. It did not, and the consequence was larger than the envelope suggests, because
the window closed. The definition's rule, that ok true is not proof of the node addressed, is
therefore not theoretical on this build.

E2 still passes, because the row is written to be satisfiable whichever way the tool behaves: the
identity clause exists for the redirect case and this run satisfied it. The row's removal clause,
which expects STALE_REF or AMBIGUOUS_TARGET with ok false, was not satisfied literally, because act 2
succeeded. That divergence is recorded rather than smoothed over. A third construction did produce
the loud refusal: a second click on a window Close ref answered WINDOW_NOT_FOUND, not_delivered.

## E2's widened refusal clause, and the code this time

The clause no longer names codes, and that widening was necessary and is now proven necessary from
both directions. rc.005 was refused WINDOW_NOT_FOUND where the row named STALE_REF and
AMBIGUOUS_TARGET. This run produced a third shape again: no refusal at all on the construction that
mattered, a success that landed on a different node.

So the honest answer to "is the widened clause satisfiable" is: yes for the refusal branch, and it is
still not the whole story, because the widening covers the wrong cases. A clause that admits any loud
refusal would have accepted this run for the wrong reason if the E2b act 2 had been refused, and it
would have said nothing at all about the silent success that actually happened. The code measured on
the redirect is not an error code at all: the envelope reports ok true, delivered_unverified,
retry unsafe, and steps[0] InvokePattern.Invoke succeeded. The clause that carries this row is the
identity clause, not the refusal wording.

## H4, line by line, with the carve-out attributed

Seven hunks between the .bak baseline and the live file. Five fall inside the allowed regions (item 3,
the browser section, the new section). Three differing lines fall outside them, and they are exactly
the three the user settled as a carve-out, each a matrix-to-scenario substitution traced to manifest
amendment sequence 6, which the .bak predates:

  1. frontmatter `description`        "appends test matrices to plans" -> "appends test scenarios"
  2. item 1 plan-section bullet       "complete test matrix ... ## Test Specification and Validation
                                      Matrix" -> "complete set of test scenarios ... ## Test
                                      Specification and Validation Scenarios"
  3. item 6 release-trigger bullet    "every check in the matrix PASS" -> "every check in the
                                      scenario table PASS"

There is no fourth. No hunk starts inside item 2, item 4 or item 5. The intended differences are the
item 3 retitle plus its new desktop bullet, the browser boundary sentence, the browser harness-choice
branch for agent-desktop with the renumbering it forces, and the 133-line insertion of
`## Desktop UAT Testing`. Evidence: logs/H4-diff.txt and logs/H4-diff-raw.txt.

## Two hazards measured, one of them weaker than its wording

  Silent discard of unsaved work (D10). A document carrying the * marker, with
  uat-d10-modified-0006 read back through the value property, was closed positionally. The close
  returned ok true, delivered_verified, process_instance_exited, with no prompt and no save bar in
  any envelope at or after it. Relaunching Notepad restored the text with its marker intact. So the
  close is SILENT, SELF CERTIFYING and RECOVERABLE BY RELAUNCH, not a verified destruction, and the
  row word discarded overstates this build.

  The save-bar branch did fire here, twice, as close-app TIMEOUT delivered_unverified with retry
  unsafe. That is the branch the row says is reachable only on a build where session saving is off.
  This build raised it anyway, for a restored draft. Each prompt was read from a fresh snapshot and
  dismissed through its own "Don't save" ref before the close was completed. That is recorded as a
  measurement, not asserted as the row's expectation.

  Silent ref redirect (E2). Set out in full above. This is the hazard that was not exercised at
  rc.005 and is exercised at rc.006.

## Three things still wrong with the matrix, stated plainly

  1. A4 cannot be satisfied literally on this host. Its clause "No package.json, lockfile ...
     entry appears" is false before this work item starts: the Agentic config repository carries
     untracked package.json and package-lock.json dated 2026-10-22, four weeks earlier, belonging to
     an unrelated dependency. The row passes on substance, that the install added nothing new, and
     rc.005 passed it the same way. The wording should say "no entry is added by this work item"
     rather than "no entry appears".

  2. G14's second clause asks the launch subsection to state that a close "can discard unsaved work
     with no prompt and still report delivered_verified". The launch subsection states the discard,
     the check before closing and the obligation to record saved or abandoned, but it does not
     mention delivered_verified and the word "hazard" appears nowhere in the file. The
     delivered_verified rule lives one subsection earlier, in the loop. A reader following both
     subsections gets every element; a reader of the launch subsection alone does not. The row passes
     on its operative test, which is whether the text tells the reader what to do, and it does. The
     placement is a wording gap for the next amendment, not a defect of this run.

  3. E2's refusal wording still does not describe what the tool does. It survived this run only
     because the identity clause carries the row. See above.

## Row-level findings that did not change a verdict

  E7, advisory. On the same ambiguity, focus-window and snapshot both refuse loudly with
  AMBIGUOUS_TARGET and a candidate list, while the unpinned find --name returned ok true with
  total_matches 0 for a control present in all three windows. The pinned form returned 1 match. A
  tester reading an empty unpinned find as absence would be misled, and the divergence within one
  tool is the finding. logs/E7-ambiguous-probe.txt.

  D6, the property must be passed as a flag. get --property value returned the marker; the positional
  attempt was rejected INVALID_ARGS with "unexpected argument value found". That rejection was
  observed in session but its envelope was overwritten by the flag-form run, so it is recorded in the
  ledger as an observation and NOT claimed as an artefact. The row does not depend on it: the saved
  help text is the proof of the property set, and get does not report available_actions, so the row's
  reading is the one the binary supports.

  D12, advisory. wait --element succeeded on a ref that still resolved, and the value comparison
  happened in the shell against a variable. No Start-Sleep appears in the recorded step.

  F2, advisory here but the reason F1's route is mandated. Through the .ps1 shim the envelope reports
  ok true with delivered_verified and verified true while the field stays empty. The value is lost
  and every field looks healthy.

## Release trigger

Every mandatory check passed with an artefact on disk, and no mandatory row is BLOCKED. This run is
the release trigger for candidate avrig/00003/rc.006 at
e006c0dc10b551f93abbb401b4caf6218a6517d7. Recommended increment: minor, because the change adds a
backward compatible capability to the tester agent with no breaking change to any product surface.

No tag, merge, bump or push was created by this run. The candidate tag, the release tag and the
version decision belong to build and to the user.

One qualification on the trigger, because it would be dishonest to state it cleanly: the definition
this run measured is not the definition on disk now. The PASS set belongs to the 46EC68BE bytes
measured at 09:50:05; a concurrent writer changed one line at 09:53:50 that no candidate tag
contains, since the file is untracked. If build is going to ship the tester definition rather than
only the repository content, re-pin the manifest to the settled file and re-score G13 first. The
product surface this plan touches in the tag is unaffected either way.
