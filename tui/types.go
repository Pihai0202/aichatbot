package main

import "time"

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type Session struct {
	ID        string    `json:"id"`
	Title     string    `json:"title"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
	Messages  []Message `json:"messages"`
}

type ProviderType string

const (
	ProviderOllama ProviderType = "ollama"
	ProviderOpenAI ProviderType = "openai"
)

type Config struct {
	ActiveProvider ProviderType `json:"active_provider"`
	OllamaBaseURL  string       `json:"ollama_base_url"`
	OllamaModel    string       `json:"ollama_model"`
	OpenAIBaseURL  string       `json:"openai_base_url"`
	OpenAIAPIKey   string       `json:"openai_api_key"`
	OpenAIModel    string       `json:"openai_model"`
	SystemPrompt   string       `json:"system_prompt"`
	Temperature    float64      `json:"temperature"`
	NumCtx         int          `json:"num_ctx"`
	RepeatPenalty  float64      `json:"repeat_penalty"`
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
		NumCtx:         4096,
		RepeatPenalty:  1.1,
	}
}

type OllamaTagsResponse struct {
	Models []struct {
		Name string `json:"name"`
	} `json:"models"`
}
