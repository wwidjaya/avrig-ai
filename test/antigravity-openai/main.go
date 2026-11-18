package main

import (
	"bufio"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

const (
	defaultClientID     = "1071006060591-tmhssin2h21lcre23" +
		"5vtolojh4g403ep.apps.googleusercontent.com"
	defaultClientSecret = "GOCSPX-K58FWR486Ld" +
		"LJ1mLB8sXC4z6qDAf"
	redirectURI         = "http://localhost:51121/oauth-callback"
	authURL             = "https://accounts.google.com/o/oauth2/v2/auth"
	tokenURL            = "https://oauth2.googleapis.com/token"
	userInfoURL         = "https://www.googleapis.com/oauth2/v1/userinfo?alt=json"
	gatewayURL          = "https://daily-cloudcode-pa.googleapis.com"
	geminiCLIURL        = "https://cloudcode-pa.googleapis.com"
	hubUserAgent        = "antigravity/hub/2.24.0 (aidev_client; os_type=windows; arch=amd64; cl=1000335682)"
)

var scopes = []string{
	"https://www.googleapis.com/auth/cloud-platform",
	"https://www.googleapis.com/auth/userinfo.email",
	"https://www.googleapis.com/auth/userinfo.profile",
	"https://www.googleapis.com/auth/cclog",
	"https://www.googleapis.com/auth/experimentsandconfigs",
}

type credentials struct {
	AccessToken  string    `json:"access_token"`
	RefreshToken string    `json:"refresh_token"`
	Project      string    `json:"project"`
	Email        string    `json:"email,omitempty"`
	ExpiresAt    time.Time `json:"expires_at"`
}

type app struct {
	credsPath string
	clientID  string
	secret    string
	http      *http.Client

	mu        sync.Mutex
	creds     credentials
	models    []string
	modelInfo map[string]availableModel
}

type availableModel struct {
	DisplayName      string     `json:"displayName,omitempty"`
	MaxTokens        int        `json:"maxTokens,omitempty"`
	MaxOutputTokens  int        `json:"maxOutputTokens,omitempty"`
	SupportsImages   bool       `json:"supportsImages,omitempty"`
	SupportsThinking bool       `json:"supportsThinking,omitempty"`
	Disabled         bool       `json:"disabled,omitempty"`
	Selectable       *bool      `json:"selectable,omitempty"`
	QuotaInfo        *quotaInfo `json:"quotaInfo,omitempty"`
}

type quotaInfo struct {
	RemainingFraction *float64 `json:"remainingFraction,omitempty"`
	ResetTime         string   `json:"resetTime,omitempty"`
}

type tokenResponse struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	ExpiresIn    int    `json:"expires_in"`
	Error        string `json:"error"`
	Description  string `json:"error_description"`
}

type upstreamError struct {
	Error struct {
		Code    int    `json:"code"`
		Message string `json:"message"`
		Status  string `json:"status"`
		Details []any  `json:"details"`
	} `json:"error"`
}

type Tool struct {
	Type     string             `json:"type"`
	Function FunctionDefinition `json:"function"`
}

type FunctionDefinition struct {
	Name        string `json:"name"`
	Description string `json:"description,omitempty"`
	Parameters  any    `json:"parameters,omitempty"`
}

type ToolCall struct {
	Index    *int             `json:"index,omitempty"`
	ID       string           `json:"id"`
	Type     string           `json:"type"`
	Function FunctionCallData `json:"function"`
}

type FunctionCallData struct {
	Name      string `json:"name,omitempty"`
	Arguments string `json:"arguments"`
}

type chatMessage struct {
	Role             string     `json:"role"`
	Content          any        `json:"content"`
	Name             string     `json:"name,omitempty"`
	ToolCalls        []ToolCall `json:"tool_calls,omitempty"`
	ToolCallID       string     `json:"tool_call_id,omitempty"`
	ReasoningContent string     `json:"reasoning_content,omitempty"`
}

type responseFormat struct {
	Type       string          `json:"type"` // "text", "json_object", "json_schema"
	JSONSchema json.RawMessage `json:"json_schema,omitempty"`
}

type streamOptions struct {
	IncludeUsage bool `json:"include_usage,omitempty"`
}

type chatRequest struct {
	Model               string          `json:"model"`
	Messages            []chatMessage   `json:"messages"`
	Temperature         *float64        `json:"temperature,omitempty"`
	TopP                *float64        `json:"top_p,omitempty"`
	MaxTokens           int             `json:"max_tokens,omitempty"`
	MaxCompletionTokens int             `json:"max_completion_tokens,omitempty"`
	MaxOutputTokens     int             `json:"max_output_tokens,omitempty"`
	Stream              bool            `json:"stream,omitempty"`
	StreamOptions       *streamOptions  `json:"stream_options,omitempty"`
	Stop                json.RawMessage `json:"stop,omitempty"`
	Tools               []Tool          `json:"tools,omitempty"`
	ToolChoice          any             `json:"tool_choice,omitempty"`
	ResponseFormat      *responseFormat `json:"response_format,omitempty"`
	ReasoningEffort     string          `json:"reasoning_effort,omitempty"`
}

type chatChoiceMessage struct {
	Role             string     `json:"role"`
	Content          *string    `json:"content"`
	ReasoningContent string     `json:"reasoning_content,omitempty"`
	ToolCalls        []ToolCall `json:"tool_calls,omitempty"`
}

type chatChoice struct {
	Index        int               `json:"index"`
	Message      chatChoiceMessage `json:"message"`
	FinishReason string            `json:"finish_reason"`
}

type chatResponse struct {
	ID      string       `json:"id"`
	Object  string       `json:"object"`
	Created int64        `json:"created"`
	Model   string       `json:"model"`
	Choices []chatChoice `json:"choices"`
	Usage   openAIUsage  `json:"usage"`
}

type googleUsage struct {
	Prompt        *int `json:"promptTokenCount"`
	Candidates    *int `json:"candidatesTokenCount"`
	Total         *int `json:"totalTokenCount"`
	Thoughts      *int `json:"thoughtsTokenCount"`
	CachedContent *int `json:"cachedContentTokenCount"`
}

type openAIUsage struct {
	PromptTokens            int                     `json:"prompt_tokens"`
	CompletionTokens        int                     `json:"completion_tokens"`
	TotalTokens             int                     `json:"total_tokens"`
	PromptTokensDetails     *promptTokenDetails     `json:"prompt_tokens_details,omitempty"`
	CompletionTokensDetails *completionTokenDetails `json:"completion_tokens_details,omitempty"`
}

type promptTokenDetails struct {
	CachedTokens int `json:"cached_tokens,omitempty"`
}

type completionTokenDetails struct {
	ReasoningTokens int `json:"reasoning_tokens,omitempty"`
}

func (u googleUsage) openAI() openAIUsage {
	result := openAIUsage{}
	if u.Prompt != nil {
		result.PromptTokens = *u.Prompt
	}
	if u.Candidates != nil {
		result.CompletionTokens = *u.Candidates
	}
	if u.Thoughts != nil {
		result.CompletionTokens += *u.Thoughts
		result.CompletionTokensDetails = &completionTokenDetails{ReasoningTokens: *u.Thoughts}
	}
	if u.Total != nil {
		result.TotalTokens = *u.Total
		if u.Prompt != nil && *u.Total >= *u.Prompt {
			// Google totalTokenCount includes thinking tokens. OpenAI completion
			// usage includes both visible output and reasoning tokens.
			result.CompletionTokens = *u.Total - *u.Prompt
		}
	} else {
		result.TotalTokens = result.PromptTokens + result.CompletionTokens
	}
	if u.CachedContent != nil && *u.CachedContent > 0 {
		result.PromptTokensDetails = &promptTokenDetails{CachedTokens: *u.CachedContent}
	}
	return result
}

func (u *googleUsage) merge(next googleUsage) {
	if next.Prompt != nil {
		u.Prompt = next.Prompt
	}
	if next.Candidates != nil {
		u.Candidates = next.Candidates
	}
	if next.Total != nil {
		u.Total = next.Total
	}
	if next.Thoughts != nil {
		u.Thoughts = next.Thoughts
	}
	if next.CachedContent != nil {
		u.CachedContent = next.CachedContent
	}
}

func (u googleUsage) hasAny() bool {
	return u.Prompt != nil || u.Candidates != nil || u.Total != nil ||
		u.Thoughts != nil || u.CachedContent != nil
}

var (
	defaultThoughtSignature = "EtcCCtQCAWkUfRPm89wedn0ZXiXQDmgjj817TCQLmCnKTOI4dnJ5EGyHBuQ4bguOuk3VzwwOKe/f1nN9kbmoBD1y+bi0paJpQ0c8YKGPSwwF5vD/lE2SBW4qgs1TBS2V8SS7+EKjS8QkPe4EpoeLXilTsMrr4f0WGjhtKut8Q/n8dXUSE/12TFTGpTj+3WttfYBOj6Rz89Q5a7+lUVJksNLhC1dtgj1Y1wt9/ymaO7iW/RTVwO4IF1XFXs2Q+qVIxaSjkyZx4e02WmFrf7hkMXKcpwwtF0kSXiPqUYmH9kYIbNPUxT+db/S/cVBSSycc2L2AJuapyZTY9J30ZBjHQHj0uUmNcwqPh+zKi4gkbSjG8sNl0gK3erQUMgtpqTtqTI3P/ClIsGdoExOxD4SECyC/PBd3eVP4C/yF+xYTb0bODyo+bJmB7NcJ01s5Mh3pIBJGuXIt61OzEA=="
	stateMu                  sync.RWMutex
	thoughtSigCache          = make(map[string]string)
	callNameCache            = make(map[string]string)
)

func setCallInfo(id, name, sig string) {
	if id == "" {
		return
	}
	stateMu.Lock()
	defer stateMu.Unlock()
	if name != "" {
		callNameCache[id] = name
	}
	if sig != "" {
		thoughtSigCache[id] = sig
	}
}

func getCallInfo(id string) (string, string) {
	stateMu.RLock()
	defer stateMu.RUnlock()
	name := callNameCache[id]
	sig := thoughtSigCache[id]
	if sig == "" {
		sig = defaultThoughtSignature
	}
	return name, sig
}

func normalizeModelID(model string) string {
	m := strings.TrimSpace(model)
	if idx := strings.LastIndex(m, "/"); idx != -1 {
		m = m[idx+1:]
	}
	if m == "default" || m == "" {
		return "gemini-3.8-flash-tiered"
	}
	return m
}

func main() {
	listen := flag.String("listen", "127.0.0.1:8085", "local OpenAI-compatible listen address")
	credsFile := flag.String("credentials", ".antigravity-token.json", "OAuth credentials file")
	flag.Parse()

	clientID := envOr("ANTIGRAVITY_CLIENT_ID", defaultClientID)
	clientSecret := envOr("ANTIGRAVITY_CLIENT_SECRET", defaultClientSecret)
	if !filepath.IsAbs(*credsFile) {
		*credsFile = filepath.Join(".", *credsFile)
	}

	a := &app{
		credsPath: *credsFile,
		clientID:  clientID,
		secret:    clientSecret,
		http:      &http.Client{Timeout: 90 * time.Second},
	}
	if err := a.loadCredentials(); err != nil {
		if !errors.Is(err, os.ErrNotExist) {
			log.Fatalf("load credentials: %v", err)
		}
		if err := a.login(); err != nil {
			log.Fatalf("OAuth login: %v", err)
		}
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", a.handleHealth)
	mux.HandleFunc("/v1/models", a.handleModels)
	mux.HandleFunc("/v1/quota", a.handleQuota)
	mux.HandleFunc("/v1/chat/completions", a.handleChatCompletions)

	server := &http.Server{
		Addr:              *listen,
		Handler:           localOnly(mux),
		ReadHeaderTimeout: 10 * time.Second,
	}
	log.Printf("Antigravity OpenAI-compatible endpoint listening at http://%s/v1", *listen)
	log.Printf("Use model IDs from GET http://%s/v1/models", *listen)
	log.Fatal(server.ListenAndServe())
}

func envOr(key, fallback string) string {
	if value := strings.TrimSpace(os.Getenv(key)); value != "" {
		return value
	}
	return fallback
}

func (a *app) loadCredentials() error {
	data, err := os.ReadFile(a.credsPath)
	if err != nil {
		if !errors.Is(err, os.ErrNotExist) {
			return err
		}
		accountFile := strings.TrimSpace(os.Getenv("ANTIGRAVITY_ACCOUNT_FILE"))
		if accountFile == "" {
			return err
		}
		data, err = os.ReadFile(accountFile)
		if err != nil {
			return fmt.Errorf("read Antigravity account file: %w", err)
		}
		var stored struct {
			Accounts []struct {
				RefreshToken     string `json:"refreshToken"`
				Email            string `json:"email"`
				ProjectID        string `json:"projectId"`
				ManagedProjectID string `json:"managedProjectId"`
				Enabled          *bool  `json:"enabled"`
			} `json:"accounts"`
		}
		if err := json.Unmarshal(data, &stored); err != nil {
			return fmt.Errorf("parse Antigravity account file: %w", err)
		}
		for _, account := range stored.Accounts {
			if account.RefreshToken == "" || (account.Enabled != nil && !*account.Enabled) {
				continue
			}
			parts := strings.SplitN(account.RefreshToken, "|", 3)
			project := account.ProjectID
			if project == "" && len(parts) > 1 {
				project = parts[1]
			}
			if project == "" {
				project = account.ManagedProjectID
			}
			if project == "" && len(parts) > 2 {
				project = parts[2]
			}
			a.creds = credentials{
				RefreshToken: parts[0],
				Project:      project,
				Email:        account.Email,
			}
			if a.creds.Project == "" {
				return fmt.Errorf("configured Antigravity account has no companion project ID")
			}
			return nil
		}
		return fmt.Errorf("Antigravity account file contains no enabled account with a refresh token")
	}
	if err := json.Unmarshal(data, &a.creds); err != nil {
		return fmt.Errorf("parse %s: %w", a.credsPath, err)
	}
	if a.creds.RefreshToken == "" {
		return fmt.Errorf("credentials file has no refresh_token")
	}
	if override := strings.TrimSpace(os.Getenv("ANTIGRAVITY_PROJECT")); override != "" {
		a.creds.Project = override
	}
	return nil
}

func (a *app) saveCredentials() error {
	if err := os.MkdirAll(filepath.Dir(a.credsPath), 0700); err != nil {
		return err
	}
	data, err := json.MarshalIndent(a.creds, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(a.credsPath, data, 0600)
}

func (a *app) login() error {
	verifierBytes := make([]byte, 32)
	if _, err := rand.Read(verifierBytes); err != nil {
		return err
	}
	verifier := base64.RawURLEncoding.EncodeToString(verifierBytes)
	sum := sha256.Sum256([]byte(verifier))
	challenge := base64.RawURLEncoding.EncodeToString(sum[:])
	stateBytes := make([]byte, 24)
	if _, err := rand.Read(stateBytes); err != nil {
		return err
	}
	state := base64.RawURLEncoding.EncodeToString(stateBytes)

	auth, _ := url.Parse(authURL)
	q := auth.Query()
	q.Set("client_id", a.clientID)
	q.Set("response_type", "code")
	q.Set("redirect_uri", redirectURI)
	q.Set("scope", strings.Join(scopes, " "))
	q.Set("state", state)
	q.Set("code_challenge", challenge)
	q.Set("code_challenge_method", "S256")
	q.Set("access_type", "offline")
	q.Set("prompt", "consent")
	auth.RawQuery = q.Encode()

	listener, err := net.Listen("tcp", "127.0.0.1:51121")
	if err != nil {
		return fmt.Errorf("listen on OAuth callback port 51121: %w", err)
	}
	defer listener.Close()

	type callback struct {
		code string
		err  error
	}
	callbackCh := make(chan callback, 1)
	callbackMux := http.NewServeMux()
	callbackMux.HandleFunc("/oauth-callback", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Query().Get("state") != state {
			http.Error(w, "OAuth state mismatch", http.StatusBadRequest)
			callbackCh <- callback{err: fmt.Errorf("OAuth state mismatch")}
			return
		}
		if oauthErr := r.URL.Query().Get("error"); oauthErr != "" {
			http.Error(w, "Google authorization failed. Return to the terminal.", http.StatusBadRequest)
			callbackCh <- callback{err: fmt.Errorf("Google OAuth: %s", oauthErr)}
			return
		}
		code := r.URL.Query().Get("code")
		if code == "" {
			http.Error(w, "Missing authorization code", http.StatusBadRequest)
			callbackCh <- callback{err: fmt.Errorf("callback did not include authorization code")}
			return
		}
		_, _ = io.WriteString(w, "Google Antigravity authorization complete. You may close this tab.")
		callbackCh <- callback{code: code}
	})
	callbackServer := &http.Server{Handler: callbackMux, ReadHeaderTimeout: 5 * time.Second}
	go func() { _ = callbackServer.Serve(listener) }()
	defer callbackServer.Close()

	fmt.Println("Opening Google OAuth in your browser...")
	fmt.Println(auth.String())
	openBrowser(auth.String())
	select {
	case result := <-callbackCh:
		if result.err != nil {
			return result.err
		}
		return a.exchangeCode(result.code, verifier)
	case <-time.After(5 * time.Minute):
		return fmt.Errorf("timed out waiting for OAuth callback")
	}
}

func openBrowser(target string) {
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "windows":
		cmd = exec.Command("rundll32", "url.dll,FileProtocolHandler", target)
	case "darwin":
		cmd = exec.Command("open", target)
	default:
		cmd = exec.Command("xdg-open", target)
	}
	_ = cmd.Start()
}

func (a *app) exchangeCode(code, verifier string) error {
	form := url.Values{
		"client_id":     {a.clientID},
		"client_secret": {a.secret},
		"code":          {code},
		"grant_type":    {"authorization_code"},
		"redirect_uri":  {redirectURI},
		"code_verifier": {verifier},
	}
	req, err := http.NewRequest(http.MethodPost, tokenURL, strings.NewReader(form.Encode()))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	var token tokenResponse
	if err := a.doJSON(req, &token); err != nil {
		return err
	}
	if token.AccessToken == "" || token.RefreshToken == "" {
		return fmt.Errorf("Google token response did not include access and refresh tokens")
	}
	a.creds = credentials{
		AccessToken:  token.AccessToken,
		RefreshToken: token.RefreshToken,
		ExpiresAt:    time.Now().Add(time.Duration(token.ExpiresIn) * time.Second),
	}
	_ = a.fetchEmail()
	if err := a.resolveProject(); err != nil {
		return err
	}
	if err := a.saveCredentials(); err != nil {
		return err
	}
	log.Printf("OAuth connected%s", emailSuffix(a.creds.Email))
	return nil
}

func emailSuffix(email string) string {
	if email == "" {
		return ""
	}
	return " as " + email
}

func (a *app) fetchEmail() error {
	req, _ := http.NewRequest(http.MethodGet, userInfoURL, nil)
	req.Header.Set("Authorization", "Bearer "+a.creds.AccessToken)
	var result struct {
		Email string `json:"email"`
	}
	if err := a.doJSON(req, &result); err != nil {
		return err
	}
	a.creds.Email = result.Email
	return nil
}

func (a *app) resolveProject() error {
	var result struct {
		Project json.RawMessage `json:"cloudaicompanionProject"`
	}
	if err := a.googlePost("/v1internal:loadCodeAssist", map[string]any{
		"metadata": map[string]string{"ideType": "ANTIGRAVITY"},
	}, &result); err != nil {
		return fmt.Errorf("resolve Antigravity project: %w", err)
	}
	if len(result.Project) == 0 {
		return fmt.Errorf("loadCodeAssist returned no project; set ANTIGRAVITY_PROJECT if your account requires one")
	}
	var projectID string
	if err := json.Unmarshal(result.Project, &projectID); err != nil {
		var project struct {
			ID string `json:"id"`
		}
		if err := json.Unmarshal(result.Project, &project); err != nil || project.ID == "" {
			return fmt.Errorf("could not parse project from loadCodeAssist")
		}
		projectID = project.ID
	}
	if override := strings.TrimSpace(os.Getenv("ANTIGRAVITY_PROJECT")); override != "" {
		projectID = override
	}
	a.creds.Project = projectID
	return nil
}

func (a *app) refreshToken(ctx context.Context) error {
	a.mu.Lock()
	defer a.mu.Unlock()
	if a.creds.AccessToken != "" && time.Until(a.creds.ExpiresAt) > 60*time.Second {
		return nil
	}
	form := url.Values{
		"client_id":     {a.clientID},
		"client_secret": {a.secret},
		"refresh_token": {a.creds.RefreshToken},
		"grant_type":    {"refresh_token"},
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, tokenURL, strings.NewReader(form.Encode()))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	var token tokenResponse
	if err := a.doJSON(req, &token); err != nil {
		return err
	}
	if token.AccessToken == "" {
		return fmt.Errorf("Google refresh response did not include an access token")
	}
	a.creds.AccessToken = token.AccessToken
	a.creds.ExpiresAt = time.Now().Add(time.Duration(token.ExpiresIn) * time.Second)
	if token.RefreshToken != "" {
		a.creds.RefreshToken = token.RefreshToken
	}
	return a.saveCredentials()
}

func (a *app) googlePost(path string, body any, out any) error {
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()
	if err := a.refreshToken(ctx); err != nil {
		return err
	}
	data, err := json.Marshal(body)
	if err != nil {
		return err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, gatewayURL+path, strings.NewReader(string(data)))
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+a.creds.AccessToken)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", hubUserAgent)
	return a.doJSON(req, out)
}

func (a *app) doJSON(req *http.Request, out any) error {
	resp, err := a.http.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(io.LimitReader(resp.Body, 8<<20))
	if err != nil {
		return err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		var apiErr upstreamError
		_ = json.Unmarshal(body, &apiErr)
		if apiErr.Error.Message != "" {
			details := ""
			if len(apiErr.Error.Details) != 0 {
				if encoded, err := json.Marshal(apiErr.Error.Details); err == nil {
					details = " details=" + string(encoded)
				}
			}
			return fmt.Errorf("upstream HTTP %d %s: %s%s", resp.StatusCode, apiErr.Error.Status, apiErr.Error.Message, details)
		}
		return fmt.Errorf("upstream HTTP %d: %s", resp.StatusCode, strings.TrimSpace(string(body)))
	}
	if out == nil {
		return nil
	}
	if err := json.Unmarshal(body, out); err != nil {
		return fmt.Errorf("decode upstream response: %w; body=%s", err, strings.TrimSpace(string(body)))
	}
	return nil
}

func (a *app) availableModels(ctx context.Context) ([]string, error) {
	a.mu.Lock()
	cached := append([]string(nil), a.models...)
	a.mu.Unlock()
	if len(cached) != 0 {
		return cached, nil
	}

	if err := a.refreshToken(ctx); err != nil {
		return nil, err
	}
	payload, _ := json.Marshal(map[string]string{"project": a.creds.Project})
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, gatewayURL+"/v1internal:fetchAvailableModels", strings.NewReader(string(payload)))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+a.creds.AccessToken)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", hubUserAgent)
	var result struct {
		Models map[string]availableModel `json:"models"`
	}
	if err := a.doJSON(req, &result); err != nil {
		return nil, err
	}
	models := make([]string, 0, len(result.Models))
	for id := range result.Models {
		models = append(models, id)
	}
	if len(models) == 0 {
		return nil, fmt.Errorf("fetchAvailableModels returned no models")
	}
	a.mu.Lock()
	a.models = models
	a.modelInfo = result.Models
	a.mu.Unlock()
	return models, nil
}

func (a *app) handleModels(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeAPIError(w, http.StatusMethodNotAllowed, "method_not_allowed", "Use GET")
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 30*time.Second)
	defer cancel()
	models, err := a.availableModels(ctx)
	if err != nil {
		writeAPIError(w, http.StatusBadGateway, "model_discovery_failed", err.Error())
		return
	}
	data := make([]map[string]any, 0, len(models))
	for _, id := range models {
		data = append(data, map[string]any{"id": id, "object": "model", "created": 0, "owned_by": "google-antigravity"})
	}
	writeJSON(w, http.StatusOK, map[string]any{"object": "list", "data": data})
}

func (a *app) handleQuota(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeAPIError(w, http.StatusMethodNotAllowed, "method_not_allowed", "Use GET")
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 15*time.Second)
	defer cancel()
	// Quota checks must refresh upstream metadata rather than serve the model
	// discovery cache, which is intentionally retained for /v1/models.
	a.mu.Lock()
	a.models = nil
	a.mu.Unlock()
	if _, err := a.availableModels(ctx); err != nil {
		writeAPIError(w, http.StatusBadGateway, "quota_fetch_failed", err.Error())
		return
	}

	a.mu.Lock()
	modelInfo := make(map[string]availableModel, len(a.modelInfo))
	for id, model := range a.modelInfo {
		modelInfo[id] = model
	}
	project := a.creds.Project
	a.mu.Unlock()

	groups := map[string]map[string]any{}
	quotaModelCount := 0
	for id, model := range modelInfo {
		if model.Disabled {
			continue
		}
		group := quotaGroup(id, model.DisplayName)
		if group == "" {
			continue
		}
		quotaModelCount++
		entry := groups[group]
		if entry == nil {
			entry = map[string]any{"modelCount": 0}
			groups[group] = entry
		}
		entry["modelCount"] = entry["modelCount"].(int) + 1
		if model.QuotaInfo == nil || model.QuotaInfo.RemainingFraction == nil {
			continue
		}
		fraction := clampFraction(*model.QuotaInfo.RemainingFraction)
		if existing, ok := entry["remainingFraction"].(float64); !ok || fraction < existing {
			entry["remainingFraction"] = fraction
			entry["remainingFractionResetTime"] = model.QuotaInfo.ResetTime
		}
		if reset := model.QuotaInfo.ResetTime; reset != "" {
			if existing, _ := entry["resetTime"].(string); existing == "" || reset < existing {
				entry["resetTime"] = reset
			}
		}
	}

	cliQuota, cliErr := a.fetchGeminiCLIQuota(ctx, project)
	result := map[string]any{
		"groups":         groups,
		"modelCount":     quotaModelCount,
		"models":         modelInfo,
		"geminiCliQuota": cliQuota,
	}
	if cliErr != nil {
		result["geminiCliQuotaError"] = cliErr.Error()
	}
	writeJSON(w, http.StatusOK, result)
}

func (a *app) fetchGeminiCLIQuota(ctx context.Context, project string) ([]map[string]any, error) {
	if err := a.refreshToken(ctx); err != nil {
		return nil, err
	}
	data, err := json.Marshal(map[string]string{"project": project})
	if err != nil {
		return nil, err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, geminiCLIURL+"/v1internal:retrieveUserQuota", strings.NewReader(string(data)))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+a.creds.AccessToken)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "google-api-nodejs-client/9.15.1")
	req.Header.Set("X-Goog-Api-Client", "gl-node/22.17.0")
	req.Header.Set("Client-Metadata", "ideType=IDE_UNSPECIFIED,platform=PLATFORM_UNSPECIFIED,pluginType=GEMINI")
	var response struct {
		Buckets []struct {
			ModelID           string  `json:"modelId"`
			RemainingFraction float64 `json:"remainingFraction"`
			ResetTime         string  `json:"resetTime"`
		} `json:"buckets"`
	}
	if err := a.doJSON(req, &response); err != nil {
		return nil, err
	}
	quotas := make([]map[string]any, 0, len(response.Buckets))
	for _, bucket := range response.Buckets {
		if !strings.HasPrefix(bucket.ModelID, "gemini-") {
			continue
		}
		quotas = append(quotas, map[string]any{
			"modelId":           bucket.ModelID,
			"remainingFraction": clampFraction(bucket.RemainingFraction),
			"resetTime":         bucket.ResetTime,
		})
	}
	return quotas, nil
}

func quotaGroup(modelID, displayName string) string {
	name := strings.ToLower(modelID + " " + displayName)
	switch {
	case strings.Contains(name, "claude"):
		return "claude"
	case strings.Contains(name, "gemini"):
		if strings.Contains(name, "flash") || strings.Contains(name, "lite") {
			return "gemini-flash"
		}
		return "gemini-pro"
	default:
		return ""
	}
}

func clampFraction(value float64) float64 {
	if value < 0 {
		return 0
	}
	if value > 1 {
		return 1
	}
	return value
}

func (a *app) handleChatCompletions(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeAPIError(w, http.StatusMethodNotAllowed, "method_not_allowed", "Use POST")
		return
	}
	var input chatRequest
	if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 16<<20)).Decode(&input); err != nil {
		writeAPIError(w, http.StatusBadRequest, "invalid_request_error", "Invalid JSON request: "+err.Error())
		return
	}
	input.Model = normalizeModelID(input.Model)
	if input.Stream {
		a.streamChatCompletion(w, r, input)
		return
	}
	if input.Model == "" || len(input.Messages) == 0 {
		writeAPIError(w, http.StatusBadRequest, "invalid_request_error", "model and non-empty messages are required")
		return
	}
	models, err := a.availableModels(r.Context())
	if err != nil {
		writeAPIError(w, http.StatusBadGateway, "model_discovery_failed", err.Error())
		return
	}
	if !contains(models, input.Model) {
		writeAPIError(w, http.StatusBadRequest, "model_not_found", fmt.Sprintf("Model %q is not in this account's available model list", input.Model))
		return
	}
	payload, err := toAntigravityRequest(input, a.creds.Project)
	if err != nil {
		writeAPIError(w, http.StatusBadRequest, "invalid_request_error", err.Error())
		return
	}
	var upstream struct {
		Response struct {
			Candidates []struct {
				Content struct {
					Parts []struct {
						Text             string `json:"text"`
						Thought          bool   `json:"thought"`
						ThoughtSignature string `json:"thoughtSignature"`
						FunctionCall     *struct {
							Name string         `json:"name"`
							Args map[string]any `json:"args"`
							ID   string         `json:"id"`
						} `json:"functionCall"`
					} `json:"parts"`
				} `json:"content"`
				FinishReason string `json:"finishReason"`
			} `json:"candidates"`
			Usage        googleUsage `json:"usageMetadata"`
			ModelVersion string      `json:"modelVersion"`
			ResponseID   string      `json:"responseId"`
		} `json:"response"`
	}
	ctx, cancel := context.WithTimeout(r.Context(), 120*time.Second)
	defer cancel()
	if err := a.googlePostWithContext(ctx, "/v1internal:generateContent", payload, &upstream); err != nil {
		log.Printf("Antigravity generation failed: %v", err)
		writeAPIError(w, http.StatusBadGateway, "antigravity_error", err.Error())
		return
	}
	if len(upstream.Response.Candidates) == 0 {
		writeAPIError(w, http.StatusBadGateway, "empty_response", "Antigravity returned no candidates")
		return
	}
	candidate := upstream.Response.Candidates[0]
	var contentBuilder strings.Builder
	var reasoningBuilder strings.Builder
	toolCalls := make([]ToolCall, 0)

	for _, part := range candidate.Content.Parts {
		if part.Thought {
			reasoningBuilder.WriteString(part.Text)
		} else if part.Text != "" {
			contentBuilder.WriteString(part.Text)
		}
		if part.FunctionCall != nil {
			id := part.FunctionCall.ID
			if id == "" {
				id = "call_" + randomID()
			}
			setCallInfo(id, part.FunctionCall.Name, part.ThoughtSignature)
			argsBytes, _ := json.Marshal(part.FunctionCall.Args)
			tcIndex := len(toolCalls)
			toolCalls = append(toolCalls, ToolCall{
				Index: &tcIndex,
				ID:    id,
				Type:  "function",
				Function: FunctionCallData{
					Name:      part.FunctionCall.Name,
					Arguments: string(argsBytes),
				},
			})
		}
	}

	result := chatResponse{
		ID:      firstNonEmpty(upstream.Response.ResponseID, "chatcmpl-"+randomID()),
		Object:  "chat.completion",
		Created: time.Now().Unix(),
		Model:   firstNonEmpty(upstream.Response.ModelVersion, input.Model),
	}

	finish := finishReason(candidate.FinishReason)
	if len(toolCalls) > 0 {
		finish = "tool_calls"
	}
	choiceMsg := chatChoiceMessage{
		Role: "assistant",
	}
	if len(toolCalls) > 0 {
		choiceMsg.ToolCalls = toolCalls
	}
	if contentBuilder.Len() > 0 || len(toolCalls) == 0 {
		s := contentBuilder.String()
		choiceMsg.Content = &s
	}
	if reasoningBuilder.Len() > 0 {
		choiceMsg.ReasoningContent = reasoningBuilder.String()
	}

	result.Choices = []chatChoice{
		{
			Index:        0,
			Message:      choiceMsg,
			FinishReason: finish,
		},
	}
	result.Usage = upstream.Response.Usage.openAI()
	writeJSON(w, http.StatusOK, result)
}

func (a *app) googlePostWithContext(ctx context.Context, path string, body any, out any) error {
	if err := a.refreshToken(ctx); err != nil {
		return err
	}
	data, err := json.Marshal(body)
	if err != nil {
		return err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, gatewayURL+path, strings.NewReader(string(data)))
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+a.creds.AccessToken)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", hubUserAgent)
	return a.doJSON(req, out)
}

func (a *app) streamChatCompletion(w http.ResponseWriter, r *http.Request, input chatRequest) {
	if input.Model == "" || len(input.Messages) == 0 {
		writeAPIError(w, http.StatusBadRequest, "invalid_request_error", "model and non-empty messages are required")
		return
	}
	models, err := a.availableModels(r.Context())
	if err != nil {
		writeAPIError(w, http.StatusBadGateway, "model_discovery_failed", err.Error())
		return
	}
	if !contains(models, input.Model) {
		writeAPIError(w, http.StatusBadRequest, "model_not_found", fmt.Sprintf("Model %q is not in this account's available model list", input.Model))
		return
	}
	payload, err := toAntigravityRequest(input, a.creds.Project)
	if err != nil {
		writeAPIError(w, http.StatusBadRequest, "invalid_request_error", err.Error())
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Minute)
	defer cancel()
	if err := a.refreshToken(ctx); err != nil {
		writeAPIError(w, http.StatusBadGateway, "oauth_error", err.Error())
		return
	}
	data, err := json.Marshal(payload)
	if err != nil {
		writeAPIError(w, http.StatusInternalServerError, "request_encoding_error", err.Error())
		return
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, gatewayURL+"/v1internal:streamGenerateContent?alt=sse", strings.NewReader(string(data)))
	if err != nil {
		writeAPIError(w, http.StatusInternalServerError, "request_error", err.Error())
		return
	}
	req.Header.Set("Authorization", "Bearer "+a.creds.AccessToken)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "text/event-stream")
	req.Header.Set("User-Agent", hubUserAgent)
	streamClient := *a.http
	streamClient.Timeout = 0 // The request context provides the overall stream deadline.
	resp, err := streamClient.Do(req)
	if err != nil {
		writeAPIError(w, http.StatusBadGateway, "antigravity_transport_error", err.Error())
		return
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		body, _ := io.ReadAll(io.LimitReader(resp.Body, 8<<20))
		var apiErr upstreamError
		_ = json.Unmarshal(body, &apiErr)
		log.Printf(
			"Antigravity stream rejected: status=%d model=%q project=%q messages=%d prompt_chars=%d max_output_tokens=%d body=%s\nupstream_payload=%s",
			resp.StatusCode, input.Model, a.creds.Project, len(input.Messages),
			messageCharacterCount(input.Messages), requestedMaxTokens(input), strings.TrimSpace(string(body)), string(data),
		)
		message := strings.TrimSpace(string(body))
		if apiErr.Error.Message != "" {
			message = apiErr.Error.Message
			if len(apiErr.Error.Details) > 0 {
				if details, marshalErr := json.Marshal(apiErr.Error.Details); marshalErr == nil {
					message += " details=" + string(details)
				}
			}
			if apiErr.Error.Status != "" {
				message = apiErr.Error.Status + ": " + message
			}
		}
		writeAPIError(w, http.StatusBadGateway, "antigravity_error", fmt.Sprintf("upstream HTTP %d: %s", resp.StatusCode, message))
		return
	}

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("X-Accel-Buffering", "no")
	w.WriteHeader(http.StatusOK)
	flusher, _ := w.(http.Flusher)
	completionID := "chatcmpl-" + randomID()
	created := time.Now().Unix()
	model := input.Model
	writeChunk := func(delta map[string]any, finish *string) error {
		choice := map[string]any{"index": 0, "delta": delta, "finish_reason": finish}
		chunk := map[string]any{
			"id": completionID, "object": "chat.completion.chunk", "created": created,
			"model": model, "choices": []any{choice},
		}
		encoded, marshalErr := json.Marshal(chunk)
		if marshalErr != nil {
			return marshalErr
		}
		if _, writeErr := fmt.Fprintf(w, "data: %s\n\n", encoded); writeErr != nil {
			return writeErr
		}
		if flusher != nil {
			flusher.Flush()
		}
		return nil
	}
	_ = writeChunk(map[string]any{"role": "assistant"}, nil)

	scanner := newSSEScanner(resp.Body)
	var finishReasonValue *string
	var usage googleUsage
	hadToolCalls := false
	toolCallIndex := 0

	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if !strings.HasPrefix(line, "data:") {
			continue
		}
		eventData := strings.TrimSpace(strings.TrimPrefix(line, "data:"))
		if eventData == "" || eventData == "[DONE]" {
			continue
		}
		var event struct {
			Response struct {
				Candidates []struct {
					Content struct {
						Parts []struct {
							Text             string `json:"text"`
							Thought          bool   `json:"thought"`
							ThoughtSignature string `json:"thoughtSignature"`
							FunctionCall     *struct {
								Name string         `json:"name"`
								Args map[string]any `json:"args"`
								ID   string         `json:"id"`
							} `json:"functionCall"`
						} `json:"parts"`
					} `json:"content"`
					FinishReason string `json:"finishReason"`
				} `json:"candidates"`
				ModelVersion string      `json:"modelVersion"`
				Usage        googleUsage `json:"usageMetadata"`
			} `json:"response"`
		}
		if json.Unmarshal([]byte(eventData), &event) != nil {
			continue
		}
		if event.Response.ModelVersion != "" {
			model = event.Response.ModelVersion
		}
		usage.merge(event.Response.Usage)
		if len(event.Response.Candidates) == 0 {
			continue
		}
		candidate := event.Response.Candidates[0]
		for _, part := range candidate.Content.Parts {
			if part.Thought && part.Text != "" {
				if err := writeChunk(map[string]any{"reasoning_content": part.Text}, nil); err != nil {
					return
				}
			} else if part.Text != "" {
				if err := writeChunk(map[string]any{"content": part.Text}, nil); err != nil {
					return
				}
			}
			if part.FunctionCall != nil {
				hadToolCalls = true
				id := part.FunctionCall.ID
				if id == "" {
					id = "call_" + randomID()
				}
				setCallInfo(id, part.FunctionCall.Name, part.ThoughtSignature)
				argsBytes, _ := json.Marshal(part.FunctionCall.Args)
				tcDelta := []map[string]any{
					{
						"index": toolCallIndex,
						"id":    id,
						"type":  "function",
						"function": map[string]any{
							"name":      part.FunctionCall.Name,
							"arguments": string(argsBytes),
						},
					},
				}
				toolCallIndex++
				if err := writeChunk(map[string]any{"tool_calls": tcDelta}, nil); err != nil {
					return
				}
			}
		}
		if candidate.FinishReason != "" {
			reason := finishReason(candidate.FinishReason)
			finishReasonValue = &reason
		}
	}
	if err := scanner.Err(); err != nil {
		log.Printf("Antigravity stream read failed: %v", err)
		return
	}
	if hadToolCalls {
		reason := "tool_calls"
		finishReasonValue = &reason
	} else if finishReasonValue == nil {
		reason := "stop"
		finishReasonValue = &reason
	}
	_ = writeChunk(map[string]any{}, finishReasonValue)
	if usage.hasAny() {
		openAI := usage.openAI()
		usageChunk := map[string]any{
			"id": completionID, "object": "chat.completion.chunk", "created": created,
			"model": model, "choices": []any{},
			"usage": openAI,
		}
		if encoded, err := json.Marshal(usageChunk); err == nil {
			_, _ = fmt.Fprintf(w, "data: %s\n\n", encoded)
		}
	}
	_, _ = fmt.Fprint(w, "data: [DONE]\n\n")
	if flusher != nil {
		flusher.Flush()
	}
}

func newSSEScanner(reader io.Reader) *bufio.Scanner {
	scanner := bufio.NewScanner(reader)
	scanner.Buffer(make([]byte, 64*1024), 4*1024*1024)
	return scanner
}

var allowedSchemaFields = map[string]bool{
	"type":                 true,
	"format":               true,
	"description":          true,
	"nullable":             true,
	"enum":                 true,
	"maxItems":             true,
	"minItems":             true,
	"properties":           true,
	"required":             true,
	"items":                true,
	"minProperties":        true,
	"maxProperties":        true,
	"minimum":              true,
	"maximum":              true,
	"default":              true,
	"title":                true,
	"anyOf":                true,
	"allOf":                true,
	"oneOf":                true,
	"not":                  true,
	"pattern":              true,
	"minLength":            true,
	"maxLength":            true,
	"example":              true,
	"additionalProperties": true,
}

func sanitizeGeminiSchema(val any) any {
	switch v := val.(type) {
	case map[string]any:
		copyMap := make(map[string]any, len(v))
		for k, val := range v {
			copyMap[k] = val
		}

		// Handle type array, e.g. ["string", "null"]
		if typeArr, ok := copyMap["type"].([]any); ok {
			var nonNullTypes []string
			isNullable := false
			for _, t := range typeArr {
				if s, ok := t.(string); ok {
					if s == "null" {
						isNullable = true
					} else {
						nonNullTypes = append(nonNullTypes, s)
					}
				}
			}
			if isNullable {
				copyMap["nullable"] = true
			}
			if len(nonNullTypes) == 1 {
				copyMap["type"] = nonNullTypes[0]
			} else if len(nonNullTypes) > 1 {
				delete(copyMap, "type")
				anyOfList := make([]any, 0, len(nonNullTypes))
				for _, nnt := range nonNullTypes {
					anyOfList = append(anyOfList, map[string]any{"type": nnt})
				}
				copyMap["anyOf"] = anyOfList
			} else {
				copyMap["type"] = "string"
			}
		}

		// Handle exclusiveMinimum -> minimum
		if em, ok := copyMap["exclusiveMinimum"]; ok {
			if _, hasMin := copyMap["minimum"]; !hasMin {
				if copyMap["type"] == "integer" {
					switch num := em.(type) {
					case float64:
						copyMap["minimum"] = num + 1
					case int:
						copyMap["minimum"] = num + 1
					default:
						copyMap["minimum"] = em
					}
				} else {
					copyMap["minimum"] = em
				}
			}
		}

		// Handle exclusiveMaximum -> maximum
		if em, ok := copyMap["exclusiveMaximum"]; ok {
			if _, hasMax := copyMap["maximum"]; !hasMax {
				if copyMap["type"] == "integer" {
					switch num := em.(type) {
					case float64:
						copyMap["maximum"] = num - 1
					case int:
						copyMap["maximum"] = num - 1
					default:
						copyMap["maximum"] = em
					}
				} else {
					copyMap["maximum"] = em
				}
			}
		}

		// Handle const -> enum
		if c, ok := copyMap["const"]; ok {
			if _, hasEnum := copyMap["enum"]; !hasEnum {
				copyMap["enum"] = []any{c}
			}
		}

		result := make(map[string]any)
		for k, item := range copyMap {
			if !allowedSchemaFields[k] {
				continue
			}
			switch k {
			case "properties":
				if props, ok := item.(map[string]any); ok {
					cleanProps := make(map[string]any, len(props))
					for propName, propSchema := range props {
						cleanProps[propName] = sanitizeGeminiSchema(propSchema)
					}
					result[k] = cleanProps
				}
			case "items":
				result[k] = sanitizeGeminiSchema(item)
			case "anyOf", "allOf", "oneOf":
				if list, ok := item.([]any); ok {
					cleanList := make([]any, 0, len(list))
					for _, elem := range list {
						cleanList = append(cleanList, sanitizeGeminiSchema(elem))
					}
					result[k] = cleanList
				}
			case "not":
				result[k] = sanitizeGeminiSchema(item)
			default:
				result[k] = item
			}
		}
		return result
	case []any:
		res := make([]any, 0, len(v))
		for _, item := range v {
			res = append(res, sanitizeGeminiSchema(item))
		}
		return res
	default:
		return val
	}
}

func toAntigravityRequest(input chatRequest, project string) (map[string]any, error) {
	contents := make([]map[string]any, 0, len(input.Messages))
	systemParts := make([]map[string]string, 0)

	for _, message := range input.Messages {
		switch message.Role {
		case "system", "developer":
			text, _ := messageText(message.Content)
			if text != "" {
				systemParts = append(systemParts, map[string]string{"text": text})
			}
		case "user":
			parts := parseUserContentParts(message.Content)
			if len(parts) > 0 {
				contents = append(contents, map[string]any{"role": "user", "parts": parts})
			}
		case "assistant":
			parts := make([]map[string]any, 0)
			if text, _ := messageText(message.Content); text != "" {
				parts = append(parts, map[string]any{"text": text})
			}
			for _, tc := range message.ToolCalls {
				var args map[string]any
				if err := json.Unmarshal([]byte(tc.Function.Arguments), &args); err != nil {
					args = map[string]any{"raw": tc.Function.Arguments}
				}
				name, sig := getCallInfo(tc.ID)
				if tc.Function.Name != "" {
					name = tc.Function.Name
				}
				setCallInfo(tc.ID, name, sig)
				fcPart := map[string]any{
					"functionCall": map[string]any{
						"name": name,
						"args": args,
						"id":   tc.ID,
					},
				}
				if strings.Contains(input.Model, "gemini") {
					fcPart["thoughtSignature"] = sig
				}
				parts = append(parts, fcPart)
			}
			if len(parts) > 0 {
				contents = append(contents, map[string]any{"role": "model", "parts": parts})
			}
		case "tool":
			tcID := message.ToolCallID
			name, _ := getCallInfo(tcID)
			if message.Name != "" {
				name = message.Name
			}
			rawStr, _ := messageText(message.Content)
			var respObj any
			var jsonMap map[string]any
			if err := json.Unmarshal([]byte(rawStr), &jsonMap); err == nil {
				respObj = jsonMap
			} else {
				respObj = map[string]any{"output": rawStr}
			}
			frPart := map[string]any{
				"functionResponse": map[string]any{
					"name":     name,
					"response": respObj,
					"id":       tcID,
				},
			}
			// Merge consecutive tool responses into a single user turn
			if len(contents) > 0 && contents[len(contents)-1]["role"] == "user" {
				lastParts, ok := contents[len(contents)-1]["parts"].([]map[string]any)
				if ok && len(lastParts) > 0 {
					if _, hasFR := lastParts[0]["functionResponse"]; hasFR {
						contents[len(contents)-1]["parts"] = append(lastParts, frPart)
						continue
					}
				}
			}
			contents = append(contents, map[string]any{
				"role":  "user",
				"parts": []map[string]any{frPart},
			})
		default:
			return nil, fmt.Errorf("unsupported message role %q", message.Role)
		}
	}

	if len(contents) == 0 {
		if len(systemParts) > 0 {
			var sb strings.Builder
			for _, part := range systemParts {
				if t := strings.TrimSpace(part["text"]); t != "" {
					if sb.Len() > 0 {
						sb.WriteString("\n\n")
					}
					sb.WriteString(t)
				}
			}
			contents = append(contents, map[string]any{
				"role":  "user",
				"parts": []map[string]any{{"text": sb.String()}},
			})
		} else {
			return nil, fmt.Errorf("messages must include at least one message")
		}
	} else if len(systemParts) != 0 {
		var sb strings.Builder
		for _, part := range systemParts {
			if t := strings.TrimSpace(part["text"]); t != "" {
				if sb.Len() > 0 {
					sb.WriteString("\n\n")
				}
				sb.WriteString(t)
			}
		}
		sysText := sb.String()
		if sysText != "" {
			prepended := false
			for _, c := range contents {
				if role, _ := c["role"].(string); role == "user" {
					if parts, ok := c["parts"].([]map[string]any); ok && len(parts) > 0 {
						if origText, hasText := parts[0]["text"].(string); hasText {
							parts[0]["text"] = sysText + "\n\n" + origText
							prepended = true
							break
						}
					}
				}
			}
			if !prepended {
				contents = append([]map[string]any{
					{"role": "user", "parts": []map[string]any{{"text": sysText}}},
				}, contents...)
			}
		}
	}

	request := map[string]any{"contents": contents}

	// Tools
	if len(input.Tools) > 0 {
		decls := make([]map[string]any, 0, len(input.Tools))
		for _, tool := range input.Tools {
			if tool.Type == "function" || tool.Type == "" {
				decl := map[string]any{
					"name":        tool.Function.Name,
					"description": tool.Function.Description,
				}
				if tool.Function.Parameters != nil {
					decl["parameters"] = sanitizeGeminiSchema(tool.Function.Parameters)
				}
				decls = append(decls, decl)
			}
		}
		if len(decls) > 0 {
			request["tools"] = []map[string]any{
				{"functionDeclarations": decls},
			}
		}
	}

	// Tool Choice
	if input.ToolChoice != nil {
		switch tc := input.ToolChoice.(type) {
		case string:
			switch strings.ToLower(tc) {
			case "none":
				request["toolConfig"] = map[string]any{
					"functionCallingConfig": map[string]any{"mode": "NONE"},
				}
			case "auto":
				request["toolConfig"] = map[string]any{
					"functionCallingConfig": map[string]any{"mode": "AUTO"},
				}
			case "required":
				request["toolConfig"] = map[string]any{
					"functionCallingConfig": map[string]any{"mode": "ANY"},
				}
			}
		case map[string]any:
			if fn, ok := tc["function"].(map[string]any); ok {
				if name, ok := fn["name"].(string); ok && name != "" {
					request["toolConfig"] = map[string]any{
						"functionCallingConfig": map[string]any{
							"mode":                 "ANY",
							"allowedFunctionNames": []string{name},
						},
					}
				}
			}
		}
	}

	generation := map[string]any{}
	if input.Temperature != nil {
		generation["temperature"] = *input.Temperature
	}
	if input.TopP != nil {
		generation["topP"] = *input.TopP
	}
	maxTokens := requestedMaxTokens(input)
	if maxTokens > 0 {
		generation["maxOutputTokens"] = maxTokens
	}
	if len(input.Stop) > 0 {
		var single string
		if err := json.Unmarshal(input.Stop, &single); err == nil && single != "" {
			generation["stopSequences"] = []string{single}
		} else {
			var multi []string
			if err := json.Unmarshal(input.Stop, &multi); err == nil && len(multi) > 0 {
				generation["stopSequences"] = multi
			}
		}
	}
	if input.ResponseFormat != nil {
		switch strings.ToLower(input.ResponseFormat.Type) {
		case "json_object":
			generation["responseMimeType"] = "application/json"
		case "json_schema":
			generation["responseMimeType"] = "application/json"
			if len(input.ResponseFormat.JSONSchema) > 0 {
				var schema any
				if err := json.Unmarshal(input.ResponseFormat.JSONSchema, &schema); err == nil {
					generation["responseSchema"] = sanitizeGeminiSchema(schema)
				}
			}
		}
	}

	// Always enable thinkingConfig to stream thoughts
	generation["thinkingConfig"] = map[string]any{
		"includeThoughts": true,
	}

	request["generationConfig"] = generation

	return map[string]any{
		"project":     project,
		"model":       input.Model,
		"request":     request,
		"userAgent":   "antigravity",
		"requestType": "agent",
		"requestId":   "agent-" + randomID(),
	}, nil
}

func parseUserContentParts(content any) []map[string]any {
	parts := make([]map[string]any, 0)
	switch val := content.(type) {
	case string:
		if val != "" {
			parts = append(parts, map[string]any{"text": val})
		}
	case []any:
		for _, item := range val {
			partMap, ok := item.(map[string]any)
			if !ok {
				continue
			}
			partType, _ := partMap["type"].(string)
			switch partType {
			case "text":
				if text, ok := partMap["text"].(string); ok && text != "" {
					parts = append(parts, map[string]any{"text": text})
				}
			case "image_url":
				if imgMap, ok := partMap["image_url"].(map[string]any); ok {
					if rawURL, ok := imgMap["url"].(string); ok {
						if strings.HasPrefix(rawURL, "data:") {
							// data:image/png;base64,...
							metaAndData := strings.SplitN(rawURL, ",", 2)
							if len(metaAndData) == 2 {
								mime := "image/jpeg"
								meta := metaAndData[0]
								if semi := strings.Index(meta, ";"); semi != -1 {
									mime = strings.TrimPrefix(meta[:semi], "data:")
								}
								parts = append(parts, map[string]any{
									"inlineData": map[string]string{
										"mimeType": mime,
										"data":     metaAndData[1],
									},
								})
							}
						}
					}
				}
			}
		}
	}
	return parts
}

func requestedMaxTokens(input chatRequest) int {
	if input.MaxTokens > 0 {
		return input.MaxTokens
	}
	if input.MaxCompletionTokens > 0 {
		return input.MaxCompletionTokens
	}
	return input.MaxOutputTokens
}

func messageCharacterCount(messages []chatMessage) int {
	total := 0
	for _, message := range messages {
		text, err := messageText(message.Content)
		if err == nil {
			total += len(text)
		}
	}
	return total
}

func messageText(content any) (string, error) {
	switch value := content.(type) {
	case string:
		return value, nil
	case []any:
		var text strings.Builder
		for _, item := range value {
			part, ok := item.(map[string]any)
			if !ok {
				continue
			}
			if s, ok := part["text"].(string); ok {
				text.WriteString(s)
			}
		}
		return text.String(), nil
	case nil:
		return "", nil
	default:
		return "", fmt.Errorf("unsupported message content type %T", content)
	}
}

func contains(values []string, expected string) bool {
	for _, value := range values {
		if value == expected {
			return true
		}
	}
	return false
}

func finishReason(value string) string {
	switch strings.ToUpper(value) {
	case "MAX_TOKENS":
		return "length"
	case "STOP":
		return "stop"
	case "SAFETY", "RECITATION":
		return "content_filter"
	default:
		return "stop"
	}
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if value != "" {
			return value
		}
	}
	return ""
}

func randomID() string {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return fmt.Sprintf("%d", time.Now().UnixNano())
	}
	return base64.RawURLEncoding.EncodeToString(b)
}

func writeAPIError(w http.ResponseWriter, status int, kind, message string) {
	writeJSON(w, status, map[string]any{"error": map[string]string{"type": kind, "message": message}})
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func localOnly(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		host, _, err := net.SplitHostPort(r.RemoteAddr)
		if err == nil {
			ip := net.ParseIP(host)
			if ip == nil || !ip.IsLoopback() {
				http.Error(w, "localhost clients only", http.StatusForbidden)
				return
			}
		}
		next.ServeHTTP(w, r)
	})
}

func (a *app) handleHealth(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"ok": true, "provider": "google-antigravity", "email": a.creds.Email})
}
