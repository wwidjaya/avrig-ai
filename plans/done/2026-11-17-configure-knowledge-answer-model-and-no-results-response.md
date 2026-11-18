---
title: "Plan: Configure Knowledge Answer Model and No-Information Response"
status: done
completed: 2026-11-18
created: 2026-11-17
author: avrig-ai
tags:
  - plan
  - backend
  - configuration
  - knowledge-assistant
---

# Plan: Configure Knowledge Answer Model and No-Information Response

## Objective

Make the model used by Knowledge Assistant answer generation configurable through the backend runtime configuration. When retrieved passages do not contain the requested information, instruct the model to clearly say that the knowledge base does not contain the information, rather than using vague wording such as “the provided passages do not contain information about ...”.

## Implementation Phases

### Phase 1: Define Configuration and Defaults

**Assignee: be**

1. Inspect current gateway configuration loading and the Knowledge Assistant SSE answer-generation path.
2. Add `answer_model: String` to the existing `ServerConfig` in `avrig-api/src/main.rs`, under the `[server]` section of the runtime `server.toml` (source default: `avrig-api/config/server.toml`; production file: `/opt/avrig/config/server.toml`). Do not add this setting to `GatewayConfig` or provider configuration: it selects the model for this server feature, while the gateway remains responsible for routing the supplied model identifier.
3. Set the default to the currently selected ChatGPT/SIWC model (`chatgpt/default`, currently resolved by the gateway to `gpt-5.6-luna`).
4. Ensure the configured value supports gateway model prefixes, for example `chatgpt/...`, `agy/...`, or `opencode/...`, and is passed through to the existing gateway client.
5. Set `answer_model = "chatgpt/default"` in production `/opt/avrig/config/server.toml`. Preserve the existing config-directory merge and precedence behavior. The setting is a non-secret model identifier; continue to redact all credential values from logs and source control.

### Phase 2: Clarify No-Information Answer Behavior

**Assignee: be**

1. Update the grounded-answer system prompt in the SSE search flow.
2. Instruct the model that if the retrieved passages do not contain the requested information, it must explicitly state that the knowledge base does not contain enough information to answer the query.
3. Do not infer an answer from unrelated passages. Keep any returned citations tied to retrieved passages and make clear they do not substantiate missing information.
4. Preserve the existing SSE event names and payload shapes.

### Phase 3: Tests and Validation

**Assignee: be**

1. Add configuration parsing/default tests for the answer-model setting.
2. Add a test verifying the configured model is used to construct the gateway request.
3. Add a prompt/behavior test for insufficient or irrelevant retrieved context, asserting the required knowledge-base-specific response instruction.
4. Verify existing grounded-answer, citation, and SSE behavior remains intact.
5. Run formatter, `cargo test -p avrig`, and release build.

### Phase 4: Deploy and Verify

**Assignee: Infra**

1. Back up the current production runtime configuration and binary.
2. Deploy the tested release binary and runtime model setting to WSL `avrig-ai`.
3. Restart `avrig.service` and verify it is healthy.
4. Test one question supported by the indexed `meaning-of-life.md` document and one question unsupported by retrieved knowledge.
5. Confirm the supported answer cites its source and the unsupported answer clearly says the knowledge base lacks the information.

## Verification Criteria

- [ ] Answer-generation model is read from runtime configuration, not hard-coded in the handler.
- [ ] Default model resolves to the currently selected `chatgpt/default` unless overridden.
- [ ] Configured provider prefixes route through the existing gateway correctly.
- [ ] Unsupported questions receive an explicit statement that the knowledge base lacks sufficient information.
- [ ] No unsupported answer is fabricated from unrelated passages.
- [ ] Existing JSON search and SSE contracts remain unchanged.
- [ ] Backend tests/build pass and production behavior is verified.

## Plan Audit

The plan keeps model selection in runtime configuration while reusing the existing gateway and model-prefix routing. It distinguishes the retrieval result from answer-generation behavior, preserves the established SSE contract, avoids changing database/schema or frontend concerns, and assigns runtime deployment to `Infra`. Validation covers both supported and unsupported questions and checks that no secrets enter source control or logs.

### Analyst Review

The analyst required the configuration owner to be explicit. The plan now assigns the setting to `ServerConfig.answer_model`, configured under `[server]` in `server.toml`. It explicitly excludes `GatewayConfig`, preserves directory-merge precedence, and retains secret-redaction requirements.
