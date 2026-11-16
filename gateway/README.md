# Mock OpenAI Gateway Service

A lightweight, standalone OpenAI-compatible mock gateway built in Go with standard library `net/http`.

## Features

- **OpenAI Chat Completions (`POST /v1/chat/completions`)**: Accepts standard OpenAI chat completion JSON payloads.
  - Supports non-streaming responses returning `"ok"` content.
  - Supports Server-Sent Events (SSE) streaming (`stream: true`) with chunks conforming to `chat.completion.chunk`.
  - Supports stream token usage statistics via `stream_options: {"include_usage": true}`.
- **OpenAI Models List (`GET /v1/models`)**: Returns a standard OpenAI model list including `default` and `gpt-4o`.
- **Health Check (`GET /` & `GET /healthz`)**: Returns HTTP 200 OK (`ok` text and `{"status":"ok"}` JSON).
- **Configurable Port**: Configured via the `PORT` environment variable (defaults to `8080`).

## Running Locally

Run directly with Go:

```powershell
go run main.go
```

Or specify a custom port:

```powershell
$env:PORT="9000"; go run main.go
```

## Usage Examples

### 1. Non-Streaming Chat Completion

**curl**:
```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**PowerShell**:
```powershell
Invoke-RestMethod -Uri "http://localhost:8080/v1/chat/completions" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"model":"gpt-4o","messages":[{"role":"user","content":"Hello"}]}'
```

### 2. SSE Streaming Chat Completion

**curl**:
```bash
curl -N -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": true,
    "stream_options": {"include_usage": true}
  }'
```

**PowerShell (streaming SSE chunks)**:
```powershell
$body = @{
    model = "gpt-4o"
    messages = @(@{ role = "user"; content = "Hello" })
    stream = $true
    stream_options = @{ include_usage = $true }
} | ConvertTo-Json

$request = [System.Net.HttpWebRequest]::Create("http://localhost:8080/v1/chat/completions")
$request.Method = "POST"
$request.ContentType = "application/json"

$streamWriter = [System.IO.StreamWriter]::new($request.GetRequestStream())
$streamWriter.Write($body)
$streamWriter.Flush()
$streamWriter.Close()

$response = $request.GetResponse()
$streamReader = [System.IO.StreamReader]::new($response.GetResponseStream())
while (-not $streamReader.EndOfStream) {
    $line = $streamReader.ReadLine()
    if ($line) {
        Write-Output $line
    }
}
$streamReader.Close()
$response.Close()
```

## Running Tests

Run the test suite:

```powershell
go test -v ./...
```
