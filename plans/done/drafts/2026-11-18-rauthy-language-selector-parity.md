# Rauthy Login Language Selector Parity with Landing Page

Status: superseded by 2026-11-18-release-0.3.0-consolidated.md
Owner: plan (authoring), fe (styles), Infra (deploy), tester (verification)
Created: 2026-11-18

## Goals and Objectives

1. The language control on `https://iam.avrig.ai` login renders as a ghost chip that reads as the same component family as the landing page and console header control: no border, no filled background, mono uppercase locale code at full foreground weight, muted glyph, ghost hover.
2. The language popover uses theme tokens (`--av-surface`, `--av-line-strong`, `--av-shadow`) so it is correct in both dark and light themes, replacing the current hardcoded `#0f172a` and `rgba(255,255,255,0.08)` values that break light mode.
3. The theme switch next to it stays visually consistent, since the current stylesheet shares rules between both controls.
4. Measurable acceptance: computed style of the language trigger reports `background-color: transparent`, `border-width: 0px`, `font-size: 12px`, `text-transform: uppercase`, and label color equal to `--av-text`; glyph color equal to `--av-muted`. Verified on light and dark, at 1440px and 390px widths.
5. No CSP relaxation, no injected JavaScript (the host allows `'self'` styles and scripts only). Pure CSS.
6. Deployed live through the documented skill path, with a bumped cache-bust version, and the repo copy byte-identical to `/var/www/iam-custom/avrig-rauthy-theme.css`.

Scope decision already agreed with the user: keep Rauthy's full locale list and dropdown behavior, and match the landing page visually. Converting Rauthy to an EN/ID two-state toggle is out of scope, because the CSP blocks injected JS and `/etc/rauthy/rauthy.toml` carries no i18n block.

## Key Detailed Design

### Program Design

Reference component, for values to copy rather than import:

- `apps/web/src/modules/landing/LandingPage.tsx` lines 157 to 168: ghost `Button`, `size="sm"`, `className="gap-1.5 font-mono text-xs font-semibold"`, `Languages` icon at `size-4 text-muted-foreground`, locale as `uppercase font-bold tracking-wider`, `title` attribute switching between "Beralih ke Bahasa Indonesia (ID)" and "Switch to English (EN)".
- Console header equivalent in `apps/web/src/shell/CommandCenterLayout.tsx` uses the same ghost treatment.

Target computed values for the Rauthy trigger (dark theme):

| Property | Value | Origin |
| --- | --- | --- |
| height | 32px | matches `size="sm"` h-8 |
| padding | 0 10px | mirrors `px-3` on a compact chip |
| gap | 6px | `gap-1.5` |
| background | transparent | ghost variant |
| border | 0 | ghost variant |
| border-radius | 8px | `rounded-md` |
| font-family | `var(--av-font-mono)` | `font-mono` |
| font-size | 12px | `text-xs` |
| font-weight | 600 | `font-semibold` |
| letter-spacing | 0.05em | `tracking-wider` |
| text-transform | uppercase | landing label |
| label color | `var(--av-text)` | `text-foreground` |
| glyph color | `var(--av-muted)` | `text-muted-foreground` |
| glyph size | 15px | optically matches `size-4` |
| min-width | none (remove 64px) | chip has no fixed floor |
| hover background | `var(--av-ghost-hover)` | ghost hover |
| hover color | `var(--av-text)` | ghost hover |
| hover extras | remove `filter: brightness(1.1)`, remove border-color change | ghost has no border |
| focus-visible | `box-shadow: 0 0 0 3px var(--av-ring)` | keep existing |

Popover values:

| Property | Value |
| --- | --- |
| background | `var(--av-surface)` |
| border | `1px solid var(--av-line-strong)` |
| border-radius | 10px |
| box-shadow | `var(--av-shadow)` |
| padding | 4px |
| width | keep the current narrow 84px, verify against longest locale code |
| option row height | 30px |
| option hover | color `var(--av-text)`, background `var(--av-ghost-hover)` |
| option selected | color `var(--av-action)`, background `var(--av-raised)` |

Implementation rules:

1. Work inside section 10 of the stylesheet, "Utility cluster: theme switch + language selector, top right". Do not add a new section.
2. Split the currently shared rule. `main .container.absolute button` styles the theme switch, `main [class*="svelte-fexfbq"].absolute > div > button` styles the language trigger. Both should read as ghost chips, but the language trigger must not inherit `min-width: 64px` or a locale-independent glyph override meant for the theme icon.
3. Exactly one glyph. The stylesheet currently both sizes Rauthy's own `svg` and injects a `::before` mask icon, so the trigger can render two glyphs. Confirm the live DOM first (see the Discovery step below), then keep Rauthy's native `svg` and drop the injected `::before` block at lines 641 to 651, or the reverse. Do not leave both.
4. Keep every selector free of new hashed Svelte class names beyond the single `[class*="svelte-fexfbq"]` exception already documented in the file header. If the hash changes after a Rauthy upgrade, the fallback selectors must still apply.
5. Keep `!important` usage consistent with the surrounding file. All defensive rules in this stylesheet need it to beat Rauthy's component CSS.
6. Do not touch the token layer, the structural layer, or sections 1 to 9 and 11.

Deployment path:

- The skill wrapper `.opencode/skills/manage-rauthy/manage-rauthy.ps1` defaults `-CssPath` to `apps/web/public/custom/avrig-rauthy-theme.css`, which does not exist. The real source is `apps/web/public/avrig-rauthy-theme.css`. Fix the default and the doc comment, otherwise `update-theme` throws unless `-CssPath` is passed by hand.
- The script already computes a timestamp cache-bust (`yyyyMMddHHmmss`), rewrites `?v=` in `/etc/nginx/sites-available/iam.avrig.ai.conf`, runs `nginx -t`, and reloads. Use it rather than ad hoc `cp`.

### Target Program Files (Mandatory)

| File | Action | Purpose |
| --- | --- | --- |
| `avrig-ai/apps/web/public/avrig-rauthy-theme.css` | edit | Section 10: trigger becomes ghost chip, glyph single and muted, popover retokenized |
| `avrig-ai/.opencode/skills/manage-rauthy/manage-rauthy.ps1` | edit | Correct the default `-CssPath` and the usage example in the header comment |
| `avrig-ai/.opencode/skills/manage-rauthy/SKILL.md` | edit | Correct the documented repository source path (currently claims `apps/web/public/custom/...`) |
| `/etc/nginx/sites-available/iam.avrig.ai.conf` (WSL `avrig-ai`) | edit by script | Cache-bust `?v=` rewrite only, no structural change |
| `/var/www/iam-custom/avrig-rauthy-theme.css` (WSL `avrig-ai`) | replace by script | Deployed stylesheet, must hash-match the repo file |

### EDM Design

No EDM changes. This is a static stylesheet plus a deployment script.

## Parallel Execution Plan

| Stream | Owner | Work | Depends on |
| --- | --- | --- | --- |
| A1 Discovery | fe | Open `https://iam.avrig.ai` in wmux, snapshot the top-right cluster, record the real DOM for the trigger and popover (how many glyphs, class names, nesting) | none |
| A2 Style edit | fe | Apply the trigger and popover changes in section 10 | A1 |
| A3 Skill fix | Infra | Correct `manage-rauthy.ps1` default path and skill doc | can run parallel with A2 |
| A4 Deploy | Infra | Run `update-theme`, confirm new `?v=`, `nginx -t` pass, reload, confirm served hash equals repo hash | A2, A3 |
| A5 Visual proof | tester | Screenshots and computed styles, dark and light, 1440 and 390 | A4 |
| B1 Release | build | Rebuild `apps/web/dist`, `make build`, `make deploy` so the embedded bundle matches, then version bump | A5 plus the in-flight composync work |

## Test Specification and Validation Matrix

Authored by `tester` before implementation, executed after deploy.

| ID | Check | Method | Pass criteria |
| --- | --- | --- | --- |
| R1 | Trigger has no chrome | wmux `eval` on the login page: `getComputedStyle(trigger)` | `backgroundColor` is `rgba(0, 0, 0, 0)`, `borderTopWidth` is `0px`, `borderRadius` is `8px` |
| R2 | Type scale matches landing | computed style comparison of Rauthy trigger vs `app.avrig.ai` language button | identical `fontFamily`, `fontSize` 12px, `fontWeight` 600, `textTransform` uppercase, `letterSpacing` within 0.005em |
| R3 | Label and glyph colors | computed `color` of the locale label and of the glyph element | label equals `--av-text` resolved value, glyph equals `--av-muted` resolved value |
| R4 | Single glyph | DOM count of `svg` plus generated `::before` with a mask-image inside the trigger | exactly one visible glyph |
| R5 | Hover state | force `:hover` via `CDP` or screenshot mid-hover | background becomes `--av-ghost-hover`, no border appears, no brightness filter |
| R6 | Popover tokens | open the picker, read computed styles | background equals `--av-surface`, border color equals `--av-line-strong`, shadow non-empty |
| R7 | Light theme | switch theme to light, re-read R1, R3, R6 | no hardcoded dark values remain, text readable (contrast at least 4.5:1 for locale code) |
| R8 | Functional language switch | pick a non-default locale, reload | selection persists, page strings change, no console errors |
| R9 | No layout shift | compare the cluster bounding box before and after | the theme switch does not move more than 2px, cluster stays 20px from the top and right at 1440 |
| R10 | Narrow viewport | 390px viewport | cluster collapses without overlapping the card title, trigger stays tappable at 32px minimum |
| R11 | Deployed identity | `sha256sum` repo file vs `/var/www/iam-custom/...` vs `curl` through nginx | all three hashes equal |
| R12 | Cache-bust | `curl -s https://iam.avrig.ai/auth/v1/ | grep -o 'avrig-rauthy-theme.css?v=[0-9]*'` | value matches the timestamp of the deploy |
| R13 | Console regression | `app.avrig.ai` header language button | unchanged, still matches the landing page |

Note for the runner: `curl.exe` on this host needs `--ssl-no-revoke`, otherwise Schannel fails with `CRYPT_E_REVOCATION_OFFLINE`.

## Review Findings

To be populated by `analyst` after verification. Expected audit points: parity is measured not asserted, light theme is genuinely token-driven, no new hashed selectors, deployment went through the skill rather than a manual copy, and the repo, the served file, and the documentation all agree on the source path.
