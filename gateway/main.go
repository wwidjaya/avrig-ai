package main

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"
)

// ChatMessage represents a single message in an OpenAI chat completion.
type ChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// StreamOptions represents optional streaming configuration such as including usage stats.
type StreamOptions struct {
	IncludeUsage bool `json:"include_usage,omitempty"`
}

// ChatCompletionRequest represents an incoming OpenAI-compatible chat completion payload.
type ChatCompletionRequest struct {
	Model         string         `json:"model"`
	Messages      []ChatMessage  `json:"messages"`
	Stream        bool           `json:"stream,omitempty"`
	StreamOptions *StreamOptions `json:"stream_options,omitempty"`
	Temperature   *float64       `json:"temperature,omitempty"`
}

// ChatCompletionChoice represents one choice returned in a non-streaming chat completion response.
type ChatCompletionChoice struct {
	Index        int         `json:"index"`
	Message      ChatMessage `json:"message"`
	FinishReason string      `json:"finish_reason"`
}

// Usage captures token counts for the chat completion.
type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// ChatCompletionResponse represents the standard non-streaming OpenAI chat completion JSON response.
type ChatCompletionResponse struct {
	ID      string                 `json:"id"`
	Object  string                 `json:"object"`
	Created int64                  `json:"created"`
	Model   string                 `json:"model"`
	Choices []ChatCompletionChoice `json:"choices"`
	Usage   Usage                  `json:"usage"`
}

// ChunkDelta represents message content delta within an SSE chunk.
type ChunkDelta struct {
	Role    string `json:"role,omitempty"`
	Content string `json:"content,omitempty"`
}

// ChunkChoice represents a single choice within an SSE chunk.
type ChunkChoice struct {
	Index        int        `json:"index"`
	Delta        ChunkDelta `json:"delta"`
	FinishReason *string    `json:"finish_reason"`
}

// ChatCompletionChunk represents an SSE chunk conforming to chat.completion.chunk.
type ChatCompletionChunk struct {
	ID      string        `json:"id"`
	Object  string        `json:"object"`
	Created int64         `json:"created"`
	Model   string        `json:"model"`
	Choices []ChunkChoice `json:"choices"`
	Usage   *Usage        `json:"usage,omitempty"`
}

// ModelItem represents a single model descriptor.
type ModelItem struct {
	ID      string `json:"id"`
	Object  string `json:"object"`
	Created int64  `json:"created"`
	OwnedBy string `json:"owned_by"`
}

// ModelListResponse represents the OpenAI list models response.
type ModelListResponse struct {
	Object string      `json:"object"`
	Data   []ModelItem `json:"data"`
}

func generateID(prefix string) string {
	b := make([]byte, 12)
	_, _ = rand.Read(b)
	return prefix + hex.EncodeToString(b)
}

func handleStream(w http.ResponseWriter, req ChatCompletionRequest, model string) {
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")

	id := generateID("chatcmpl-")
	created := time.Now().Unix()

	sendChunk := func(chunk ChatCompletionChunk) {
		data, err := json.Marshal(chunk)
		if err != nil {
			return
		}
		_, _ = fmt.Fprintf(w, "data: %s\n\n", data)
		flusher.Flush()
	}

	// Chunk 1: Content delta
	sendChunk(ChatCompletionChunk{
		ID:      id,
		Object:  "chat.completion.chunk",
		Created: created,
		Model:   model,
		Choices: []ChunkChoice{
			{
				Index: 0,
				Delta: ChunkDelta{
					Role:    "assistant",
					Content: "ok",
				},
				FinishReason: nil,
			},
		},
	})

	// Chunk 2: Finish chunk
	stopReason := "stop"
	sendChunk(ChatCompletionChunk{
		ID:      id,
		Object:  "chat.completion.chunk",
		Created: created,
		Model:   model,
		Choices: []ChunkChoice{
			{
				Index:        0,
				Delta:        ChunkDelta{},
				FinishReason: &stopReason,
			},
		},
	})

	// Chunk 3: Optional usage chunk if requested via stream_options.include_usage
	if req.StreamOptions != nil && req.StreamOptions.IncludeUsage {
		sendChunk(ChatCompletionChunk{
			ID:      id,
			Object:  "chat.completion.chunk",
			Created: created,
			Model:   model,
			Choices: []ChunkChoice{},
			Usage: &Usage{
				PromptTokens:     1,
				CompletionTokens: 1,
				TotalTokens:      2,
			},
		})
	}

	// Done sentinel
	_, _ = fmt.Fprintf(w, "data: [DONE]\n\n")
	flusher.Flush()
}

// setupRouter creates and configures the HTTP routes.
func setupRouter() http.Handler {
	mux := http.NewServeMux()

	// Root and health endpoints
	mux.HandleFunc("GET /{$}", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok\n"))
	})

	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"ok"}` + "\n"))
	})

	// OpenAI GET /v1/models endpoint
	mux.HandleFunc("GET /v1/models", func(w http.ResponseWriter, r *http.Request) {
		resp := ModelListResponse{
			Object: "list",
			Data: []ModelItem{
				{
					ID:      "default",
					Object:  "model",
					Created: 1700000000,
					OwnedBy: "avrig-ai",
				},
				{
					ID:      "gpt-4o",
					Object:  "model",
					Created: 1700000000,
					OwnedBy: "avrig-ai",
				},
			},
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_ = json.NewEncoder(w).Encode(resp)
	})

	// OpenAI POST /v1/chat/completions endpoint
	mux.HandleFunc("POST /v1/chat/completions", func(w http.ResponseWriter, r *http.Request) {
		var req ChatCompletionRequest
		bodyBytes, err := io.ReadAll(r.Body)
		if err == nil && len(bodyBytes) > 0 {
			_ = json.Unmarshal(bodyBytes, &req)
		}

		model := req.Model
		if model == "" {
			model = "default"
		}

		// Handle streaming request
		if req.Stream {
			handleStream(w, req, model)
			return
		}

		// Handle standard non-streaming request
		resp := ChatCompletionResponse{
			ID:      generateID("chatcmpl-"),
			Object:  "chat.completion",
			Created: time.Now().Unix(),
			Model:   model,
			Choices: []ChatCompletionChoice{
				{
					Index: 0,
					Message: ChatMessage{
						Role:    "assistant",
						Content: "ok",
					},
					FinishReason: "stop",
				},
			},
			Usage: Usage{
				PromptTokens:     1,
				CompletionTokens: 1,
				TotalTokens:      2,
			},
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_ = json.NewEncoder(w).Encode(resp)
	})

	return mux
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	handler := setupRouter()
	addr := fmt.Sprintf(":%s", port)
	log.Printf("Gateway server listening on %s", addr)

	if err := http.ListenAndServe(addr, handler); err != nil && err != http.ErrServerClosed {
		log.Fatalf("Server error: %v", err)
	}
}
