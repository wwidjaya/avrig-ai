# Antigravity OpenAI-compatible test server

This standalone Go program authenticates with Google Antigravity OAuth, asks the
account for its available models, and exposes a local OpenAI-compatible API.
It calls Google's Antigravity gateway directly, rather than routing requests
through OpenCode's plugin.

The OAuth client ID and client secret are the public installed-client values
used by the Antigravity OAuth flow. They can be overridden with
`ANTIGRAVITY_CLIENT_ID` and `ANTIGRAVITY_CLIENT_SECRET`.

## Run

From this directory:

```powershell
go test ./...
go run .
```

On first run, the program opens Google sign-in in a browser. The callback uses
`http://localhost:51121/oauth-callback`, so that port must be free. It stores
refresh credentials in `.antigravity-token.json` with owner-only file
permissions. That file is ignored by Git. Do not share or commit it.

The companion project is discovered using `loadCodeAssist`. If you need to
override it, set `ANTIGRAVITY_PROJECT` before starting the program.

## OpenAI-compatible endpoints

- `GET http://127.0.0.1:8085/health`
- `GET http://127.0.0.1:8085/v1/models`
- `POST http://127.0.0.1:8085/v1/chat/completions`

The model list is fetched from `fetchAvailableModels`, so use the exact IDs
returned for the signed-in account. Chat completions support both JSON
responses and OpenAI-compatible SSE when `stream` is true. Tool calls and
multimodal message parts are not implemented. The server binds to loopback only.

`GET /v1/quota` returns model metadata and remaining quota from Antigravity's
`fetchAvailableModels` response, grouped into Claude, Gemini Pro, and Gemini
Flash families. It also queries the separate Gemini CLI quota endpoint and
returns its Gemini model buckets under `geminiCliQuota`. Streamed completions
include an OpenAI-style final usage chunk when Google supplies `usageMetadata`.

To run with the OAuth credentials created in the OpenCode integration setup:

```powershell
go run . -listen 127.0.0.1:8086 -credentials .oauth-login-test.json
```

Example request:

```powershell
$model = (Invoke-RestMethod http://127.0.0.1:8085/v1/models).data[0].id
$body = @{
  model = $model
  messages = @(@{ role = "user"; content = "Reply with exactly: OK" })
  max_tokens = 32
} | ConvertTo-Json -Depth 8

Invoke-RestMethod http://127.0.0.1:8085/v1/chat/completions `
  -Method Post -ContentType "application/json" -Body $body
```

Or with an OpenAI-compatible client, set the base URL to
`http://127.0.0.1:8085/v1` and use any non-empty placeholder API key.

If generation fails, the server returns Google's upstream HTTP status, status
name, and message in the OpenAI-style error response. This is the important
diagnostic distinction from quota discovery.
