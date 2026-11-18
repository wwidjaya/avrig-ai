# ChatGPT / OpenAI OAuth Test

A Rust CLI application demonstrating OAuth2 Authorization Code flow with PKCE to authenticate and connect to ChatGPT / OpenAI APIs.

## How it works

1. Generates PKCE code challenge and verifier with a secure CSRF state token.
2. Spawns an ephemeral local HTTP server on `http://localhost:8080/callback`.
3. Prompts the user to log in via their browser using OpenAI's OAuth authorization endpoint.
4. Receives the redirect callback containing the authorization code and validates the CSRF token.
5. Exchanges the authorization code for an access token via the OAuth token endpoint.
6. Makes a test request with the bearer access token to OpenAI chat completions (`/v1/chat/completions`).

## Configuration

Set the environment variables in `test/.env` or export them in your shell:

### For ChatGPT / OpenAI (SIWC):
```env
OPENAI_OAUTH_CLIENT_ID=dynamic_agent_client
OPENAI_AUTH_URL=https://auth.openai.com/api/accounts/authorize
OPENAI_TOKEN_URL=https://auth.openai.com/api/accounts/oauth/token
OPENAI_REDIRECT_URL=http://127.0.0.1:8080/callback
OPENAI_MODEL=gpt-5.6-luna
```

### For Google Gemini OAuth:
```env
GOOGLE_OAUTH_CLIENT_ID=your_google_desktop_oauth_client_id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your_google_client_secret_optional_for_desktop
GOOGLE_REDIRECT_URI=http://127.0.0.1:8085/callback
GOOGLE_GEMINI_MODEL=gemini-2.5-flash
```

## Running the applications

### ChatGPT OAuth (SIWC)
```powershell
cargo run -p chatgpt_oauth_test
```

### Google Gemini OAuth (Custom GCP Desktop App)
```powershell
cargo run -p chatgpt_oauth_test --bin gemini_oauth_test
```

### OpenCode / Gemini CLI OAuth (Zero-Config / Free Gemini)
```powershell
cargo run -p chatgpt_oauth_test --bin opencode_gemini_oauth
```

### Antigravity OpenAI-Compatible Gateway Server (Rust version of Go gateway)
```powershell
# Run with defaults (127.0.0.1:8085, .antigravity-token.json)
cargo run -p chatgpt_oauth_test --bin antigravity-openai

# Custom listen address and credentials file
cargo run -p chatgpt_oauth_test --bin antigravity-openai -- --listen 127.0.0.1:8086 --credentials .oauth-login-test.json

# Or using the alias binary name:
cargo run -p chatgpt_oauth_test --bin antigravity-gateway
```
