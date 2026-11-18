package main

import (
	"encoding/json"
	"testing"
)

func TestToAntigravityRequest(t *testing.T) {
	temp := 0.25
	input := chatRequest{
		Model:       "gemini-3.8-flash",
		Temperature: &temp,
		MaxTokens:   64,
		Messages: []chatMessage{
			{Role: "system", Content: "Be concise."},
			{Role: "user", Content: "Hi"},
			{Role: "assistant", Content: "Hello"},
			{Role: "user", Content: "How are you?"},
		},
	}

	got, err := toAntigravityRequest(input, "project-123")
	if err != nil {
		t.Fatal(err)
	}
	if got["project"] != "project-123" || got["model"] != input.Model {
		t.Fatalf("unexpected envelope: %#v", got)
	}
	request := got["request"].(map[string]any)
	contents := request["contents"].([]map[string]any)
	if len(contents) != 3 || contents[1]["role"] != "model" {
		t.Fatalf("assistant role was not mapped to model: %#v", contents)
	}
	system := request["systemInstruction"].(map[string]any)
	parts := system["parts"].([]map[string]string)
	if parts[0]["text"] != "Be concise." {
		t.Fatalf("system instruction was not preserved: %#v", system)
	}
	config := request["generationConfig"].(map[string]any)
	if config["maxOutputTokens"] != 64 || config["temperature"] != temp {
		t.Fatalf("generation config not mapped: %#v", config)
	}
	if _, err := json.Marshal(got); err != nil {
		t.Fatalf("request is not JSON encodable: %v", err)
	}
}

func TestMessageText(t *testing.T) {
	got, err := messageText([]any{
		map[string]any{"type": "text", "text": "one"},
		map[string]any{"type": "text", "text": " two"},
	})
	if err != nil {
		t.Fatal(err)
	}
	if got != "one two" {
		t.Fatalf("got %q", got)
	}
}

func TestQuotaGroup(t *testing.T) {
	tests := []struct {
		model, display, want string
	}{
		{"claude-opus-5", "", "claude"},
		{"gemini-3.8-flash-medium", "Gemini Flash", "gemini-flash"},
		{"gemini-2.5-pro", "Gemini Pro", "gemini-pro"},
		{"gpt-oss-120b", "", ""},
	}
	for _, test := range tests {
		if got := quotaGroup(test.model, test.display); got != test.want {
			t.Errorf("quotaGroup(%q, %q) = %q, want %q", test.model, test.display, got, test.want)
		}
	}
}

func TestClampFraction(t *testing.T) {
	for _, test := range []struct {
		input, want float64
	}{{-0.1, 0}, {0.5, 0.5}, {1.1, 1}} {
		if got := clampFraction(test.input); got != test.want {
			t.Errorf("clampFraction(%v) = %v, want %v", test.input, got, test.want)
		}
	}
}

func TestGoogleUsageOpenAIIncludesThoughtTokens(t *testing.T) {
	prompt, candidates, total, thoughts, cached := 8, 3, 68, 57, 2
	got := (googleUsage{
		Prompt:        &prompt,
		Candidates:    &candidates,
		Total:         &total,
		Thoughts:      &thoughts,
		CachedContent: &cached,
	}).openAI()
	if got.PromptTokens != 8 || got.CompletionTokens != 60 || got.TotalTokens != 68 {
		t.Fatalf("unexpected usage totals: %#v", got)
	}
	if got.CompletionTokensDetails == nil || got.CompletionTokensDetails.ReasoningTokens != 57 {
		t.Fatalf("reasoning usage missing: %#v", got)
	}
	if got.PromptTokensDetails == nil || got.PromptTokensDetails.CachedTokens != 2 {
		t.Fatalf("cached prompt usage missing: %#v", got)
	}
}

func TestGoogleUsageMergeKeepsEarlierPartialCounts(t *testing.T) {
	prompt, total := 8, 68
	candidates := 0
	var usage googleUsage
	usage.merge(googleUsage{Prompt: &prompt, Total: &total})
	usage.merge(googleUsage{Candidates: &candidates})
	if !usage.hasAny() || usage.Prompt == nil || *usage.Prompt != 8 ||
		usage.Total == nil || *usage.Total != 68 ||
		usage.Candidates == nil || *usage.Candidates != 0 {
		t.Fatalf("partial usage was not merged: %#v", usage)
	}
}
