# Schema reference: keys used by manage-zeroclaw

Authoritative source: https://docs.zeroclawlabs.ai/master/en/reference/config.html (generated from the live schema). Values below are defaults; check that page for full per-key docs before relying on a numeric threshold.

## [skills] loading config
| key | type | default | meaning |
|---|---|---|---|
| allow_scripts | bool | false | scripts blocked unless true (this install already true) |
| skill_creation.enabled | bool | false | auto-create SKILL.toml from tool-call trace |
| skill_creation.max_skills | int | 500 | LRU cap on auto-created skills |
| skill_creation.similarity_threshold | float | 0.85 | embedding-dedup cutoff |
| skill_creation.reflection_enabled | bool | false | opt-in; needs enabled |

## Skill bundles: [skill_bundles.<alias>]
- Named bundle; `directory` optional - resolves to `<install>/shared/skills/<alias>/` when omitted. Attach alias in `[agents.<a>].skill_bundles`.
- Each listed alias resolves to a skill directory; agents load it at runtime.

## [agents.<alias>]
| key | type | default | meaning |
|---|---|---|---|
| enabled | bool | true | false disables the agent |
| channels | string[] | [] | channel aliases it handles |
| model_provider | string | — | ref to `[providers.models.<type>.<alias>]` |
| risk_profile | string | — | ref to `[risk_profiles.<type>.<alias>]` |
| runtime_profile | string | — | ref to `[runtime_profiles.<type>.<alias>]` |
| skill_bundles | string[] | [] | bundle aliases; append here to attach |
| delegate_same_risk_profile | bool | true | auto-allow delegation to same-risk-profile agents |
| delegates | object[] | [] | explicit additional delegate roster |
| precheck.enabled/timeout_secs | bool/int | true/5 | channel reply-intent precheck |
| identity.format | string | "openclaw" | agent card format |
| a2a.published | bool | false | publish as discoverable A2A agent |

## [channels.<type>.<alias>] (one instance per type)
| key | type | default | meaning |
|---|---|---|---|
| enabled | bool | true | master switch for the channel |
| dm_policy / group_policy | string | — | allowlist default; gate inbound peers |
| mode | string | personal | e.g. whatsapp |
| interrupt_on_new_message | bool | false | |
| mention_only | bool | false | only on mentions |
| approval_timeout_secs | int | 300 | |
| self_chat_mode | bool | false | |

Channel types in registry: amqp, bluesky, clawdtalk, cli, dingtalk, discord, email, filesystem, git, gmail_push, imessage, irc, lark, line, linq, matrix, mattermost, mochat, mqtt, nextcloud_talk, nostr, plugin, qq, reddit, slack, telegram, twitch, twitter, voice_call, voice_duplex, voice_wake, webhook, wechat, wecom, wecom_ws, whatsapp.

## [risk_profiles.<alias>]
| key | type | default | meaning |
|---|---|---|---|
| level | string | — | full / supervised (autonomy) |
| workspace_only | bool | true | default; block outside workspace |
| allowed_tools | string[] | [] | explicit allow |
| excluded_tools | string[] | [] | |
| forbidden_paths | string[] | [] | block paths |
| required_approval_for_medium_risk | bool | true | |
| block_high_risk_commands | bool | true | |
| allowed_commands | string[] | [] | |
| auto_approve | string[] | [] | pre-approved tools |
| delegation_policy.mode | string | forbidden | |
| shell_env_passthrough | string[] | [] | |

## [runtime_profiles.<alias>] (named execution profiles)
Sub-profiles under `[runtime_profiles.default.<sub>]`:
- `tool_receipts.enabled` (false default), inject_system_prompt, show_in_response.
- `context_compression.enabled` (false), summary_max_chars, protect_first_n, threshold_ratio.
- `thinking.default_level` ("medium"), native_thinking.
- `history_pruning.max_tokens`, keep_recent, collapse_tool_results.

## [providers.models.<type>.<alias>]
- Shape: `kind`, `wire_api`, `uri`, `model`, `api_key`. OpenAI-compatible kind used for custom gateways; normal subscriptions use stored auth not `api_key`.

## [gateway]
| key | type | default | meaning |
|---|---|---|---|
| host | string | — | 0.0.0.0 when exposed |
| allow_public_bind | bool | false | |
| allow_remote_admin | bool | false | |
| web_dist_dir | string | — | static asset dir |

## [memory] (per-agent) backend | string | sqlite | persistent contract.
## [tunnel.*] | enabled=false per tunnel provider (tailscale, ngrok, pinggy, cloudflare, custom).
## [transcription.<type>] and [tts.*] | type wrappers; define a provider to set agent providers.

## Notes
- Secrets are opaque (`enc2:`). Keep byte-identical.
- `schema_version = 3` current in this install; do not bump without reason.
- Prefer pane edits when a `zerocode` session is open; headless edits only for terminal/headless provisioning.
