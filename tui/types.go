package main

import "time"

// Message represents a single message in a conversation
type Message struct {
	Role    string `json:"role"`    // "system", "user", "assistant"
	Content string `json:"content"`
}

// Session represents a chat conversation history
type Session struct {
	ID        string    `json:"id"`
	Title     string    `json:"title"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
	Messages  []Message `json:"messages"`
}

// ProviderType represents the AI backend provider
type ProviderType string

const (
	ProviderOllama ProviderType = "ollama"
	ProviderOpenAI ProviderType = "openai"
)

// Config holds user configuration and settings
type Config struct {
	ActiveProvider ProviderType `json:"active_provider"`
	OllamaBaseURL  string       `json:"ollama_base_url"`
	OllamaModel    string       `json:"ollama_model"`
	OpenAIBaseURL  string       `json:"openai_base_url"`
	OpenAIAPIKey   string       `json:"openai_api_key"`
	OpenAIModel    string       `json:"openai_model"`
	SystemPrompt   string       `json:"system_prompt"`
	Temperature    float64      `json:"temperature"`
}

func DefaultConfig() Config {
	return Config{
		ActiveProvider: ProviderOllama,
		OllamaBaseURL:  "http://localhost:11434",
		OllamaModel:    "llama3:latest",
		OpenAIBaseURL:  "https://api.openai.com/v1",
		OpenAIAPIKey:   "",
		OpenAIModel:    "gpt-4o-mini",
		SystemPrompt:   "You are a helpful, concise, and intelligent AI assistant.",
		Temperature:    0.7,
	}
}

// OllamaTagsResponse represents Ollama /api/tags response
type OllamaTagsResponse struct {
	Models []struct {
		Name string `json:"name"`
	} `json:"models"`
}
