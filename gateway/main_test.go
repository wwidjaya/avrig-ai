package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestRootEndpoint(t *testing.T) {
	router := setupRouter()
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}

	body := strings.TrimSpace(rec.Body.String())
	if body != "ok" {
		t.Fatalf("expected body 'ok', got %q", body)
	}
}

func TestHealthzEndpoint(t *testing.T) {
	router := setupRouter()
	req := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}

	var res map[string]string
	if err := json.NewDecoder(rec.Body).Decode(&res); err != nil {
		t.Fatalf("failed to parse json response: %v", err)
	}

	if res["status"] != "ok" {
		t.Fatalf("expected status 'ok', got %q", res["status"])
	}
}

func TestModelsEndpoint(t *testing.T) {
	router := setupRouter()
	req := httptest.NewRequest(http.MethodGet, "/v1/models", nil)
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}

	var res ModelListResponse
	if err := json.NewDecoder(rec.Body).Decode(&res); err != nil {
		t.Fatalf("failed to decode models response: %v", err)
	}

	if res.Object != "list" {
		t.Fatalf("expected object 'list', got %q", res.Object)
	}

	if len(res.Data) == 0 {
		t.Fatalf("expected at least one model in list")
	}

	foundDefault := false
	for _, m := range res.Data {
		if m.ID == "default" || m.ID == "gpt-4o" {
			foundDefault = true
			break
		}
	}

	if !foundDefault {
		t.Fatalf("expected model 'default' or 'gpt-4o' to be present")
	}
}

func TestChatCompletionsEndpoint(t *testing.T) {
	router := setupRouter()

	payload := ChatCompletionRequest{
		Model: "gpt-4o",
		Messages: []ChatMessage{
			{
				Role:    "user",
				Content: "Hello world",
			},
		},
	}
	raw, _ := json.Marshal(payload)

	req := httptest.NewRequest(http.MethodPost, "/v1/chat/completions", bytes.NewReader(raw))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}

	var res ChatCompletionResponse
	if err := json.NewDecoder(rec.Body).Decode(&res); err != nil {
		t.Fatalf("failed to decode chat completion response: %v", err)
	}

	if res.Model != "gpt-4o" {
		t.Fatalf("expected model 'gpt-4o', got %q", res.Model)
	}

	if len(res.Choices) == 0 {
		t.Fatalf("expected choices in response")
	}

	content := res.Choices[0].Message.Content
	if content != "ok" {
		t.Fatalf("expected message content 'ok', got %q", content)
	}
}

func TestChatCompletionsEmptyPayload(t *testing.T) {
	router := setupRouter()

	req := httptest.NewRequest(http.MethodPost, "/v1/chat/completions", nil)
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}

	var res ChatCompletionResponse
	if err := json.NewDecoder(rec.Body).Decode(&res); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if res.Choices[0].Message.Content != "ok" {
		t.Fatalf("expected message content 'ok', got %q", res.Choices[0].Message.Content)
	}
}

func TestChatCompletionsStreaming(t *testing.T) {
	router := setupRouter()

	payload := ChatCompletionRequest{
		Model: "gpt-4o",
		Messages: []ChatMessage{
			{
				Role:    "user",
				Content: "Hello streaming",
			},
		},
		Stream: true,
	}
	raw, _ := json.Marshal(payload)

	req := httptest.NewRequest(http.MethodPost, "/v1/chat/completions", bytes.NewReader(raw))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}

	contentType := rec.Header().Get("Content-Type")
	if !strings.HasPrefix(contentType, "text/event-stream") {
		t.Fatalf("expected Content-Type text/event-stream, got %q", contentType)
	}

	scanner := bufio.NewScanner(rec.Body)
	var dataLines []string
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "data: ") {
			dataLines = append(dataLines, strings.TrimPrefix(line, "data: "))
		}
	}

	if len(dataLines) < 3 {
		t.Fatalf("expected at least 3 SSE data lines, got %d", len(dataLines))
	}

	// Verify Chunk 1: content "ok"
	var chunk1 ChatCompletionChunk
	if err := json.Unmarshal([]byte(dataLines[0]), &chunk1); err != nil {
		t.Fatalf("failed to unmarshal chunk 1: %v", err)
	}
	if len(chunk1.Choices) == 0 || chunk1.Choices[0].Delta.Content != "ok" {
		t.Fatalf("expected chunk 1 content 'ok', got %+v", chunk1.Choices)
	}

	// Verify Chunk 2: finish_reason "stop"
	var chunk2 ChatCompletionChunk
	if err := json.Unmarshal([]byte(dataLines[1]), &chunk2); err != nil {
		t.Fatalf("failed to unmarshal chunk 2: %v", err)
	}
	if len(chunk2.Choices) == 0 || chunk2.Choices[0].FinishReason == nil || *chunk2.Choices[0].FinishReason != "stop" {
		t.Fatalf("expected chunk 2 finish_reason 'stop', got %+v", chunk2.Choices)
	}

	// Verify Done line
	lastLine := dataLines[len(dataLines)-1]
	if lastLine != "[DONE]" {
		t.Fatalf("expected final data line to be [DONE], got %q", lastLine)
	}
}

func TestChatCompletionsStreamingWithUsage(t *testing.T) {
	router := setupRouter()

	payload := ChatCompletionRequest{
		Model: "gpt-4o",
		Messages: []ChatMessage{
			{
				Role:    "user",
				Content: "Hello with usage",
			},
		},
		Stream: true,
		StreamOptions: &StreamOptions{
			IncludeUsage: true,
		},
	}
	raw, _ := json.Marshal(payload)

	req := httptest.NewRequest(http.MethodPost, "/v1/chat/completions", bytes.NewReader(raw))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}

	scanner := bufio.NewScanner(rec.Body)
	var dataLines []string
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "data: ") {
			dataLines = append(dataLines, strings.TrimPrefix(line, "data: "))
		}
	}

	foundUsage := false
	for _, line := range dataLines {
		if line == "[DONE]" {
			continue
		}
		var chunk ChatCompletionChunk
		if err := json.Unmarshal([]byte(line), &chunk); err == nil {
			if chunk.Usage != nil {
				foundUsage = true
				if chunk.Usage.TotalTokens != 2 {
					t.Fatalf("expected total_tokens 2, got %d", chunk.Usage.TotalTokens)
				}
				if len(chunk.Choices) != 0 {
					t.Fatalf("expected empty choices on usage chunk, got %d", len(chunk.Choices))
				}
			}
		}
	}

	if !foundUsage {
		t.Fatalf("expected usage chunk when stream_options.include_usage is true")
	}
}
