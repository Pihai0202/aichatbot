package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

type TokenMsg string
type StreamDoneMsg struct{}
type StreamErrMsg struct{ Err error }

type AIClient struct {
	httpClient *http.Client
}

func NewAIClient() *AIClient {
	return &AIClient{
		httpClient: &http.Client{Timeout: 0}, // No timeout for streaming
	}
}

// FetchOllamaModels queries local Ollama tags
func (c *AIClient) FetchOllamaModels(baseURL string) ([]string, error) {
	url := strings.TrimRight(baseURL, "/") + "/api/tags"
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, err
	}

	client := &http.Client{Timeout: 3 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	var res OllamaTagsResponse
	if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
		return nil, err
	}

	var names []string
	for _, m := range res.Models {
		names = append(names, m.Name)
	}
	return names, nil
}

// StreamResponse streams tokens from either Ollama or OpenAI
func (c *AIClient) StreamResponse(cfg Config, messages []Message, tokenChan chan<- string, errChan chan<- error) {
	if cfg.ActiveProvider == ProviderOllama {
		c.streamOllama(cfg, messages, tokenChan, errChan)
	} else {
		c.streamOpenAI(cfg, messages, tokenChan, errChan)
	}
}

func (c *AIClient) streamOllama(cfg Config, messages []Message, tokenChan chan<- string, errChan chan<- error) {
	url := strings.TrimRight(cfg.OllamaBaseURL, "/") + "/api/chat"

	reqMsgs := make([]map[string]string, 0)
	if cfg.SystemPrompt != "" {
		reqMsgs = append(reqMsgs, map[string]string{"role": "system", "content": cfg.SystemPrompt})
	}
	for _, m := range messages {
		reqMsgs = append(reqMsgs, map[string]string{"role": m.Role, "content": m.Content})
	}

	payload := map[string]interface{}{
		"model":    cfg.OllamaModel,
		"messages": reqMsgs,
		"options": map[string]interface{}{
			"temperature": cfg.Temperature,
		},
		"stream": true,
	}

	bodyBytes, _ := json.Marshal(payload)
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(bodyBytes))
	if err != nil {
		errChan <- err
		return
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		errChan <- fmt.Errorf("Failed to connect to Ollama at %s: %v", url, err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		errChan <- fmt.Errorf("Ollama API Error (%d): %s", resp.StatusCode, string(body))
		return
	}

	scanner := bufio.NewScanner(resp.Body)
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}

		var chunk struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
			Done bool `json:"done"`
		}

		if err := json.Unmarshal(line, &chunk); err == nil {
			if chunk.Message.Content != "" {
				tokenChan <- chunk.Message.Content
			}
			if chunk.Done {
				break
			}
		}
	}

	if err := scanner.Err(); err != nil {
		errChan <- err
	} else {
		close(tokenChan)
	}
}

func (c *AIClient) streamOpenAI(cfg Config, messages []Message, tokenChan chan<- string, errChan chan<- error) {
	url := strings.TrimRight(cfg.OpenAIBaseURL, "/") + "/chat/completions"

	reqMsgs := make([]map[string]string, 0)
	if cfg.SystemPrompt != "" {
		reqMsgs = append(reqMsgs, map[string]string{"role": "system", "content": cfg.SystemPrompt})
	}
	for _, m := range messages {
		reqMsgs = append(reqMsgs, map[string]string{"role": m.Role, "content": m.Content})
	}

	payload := map[string]interface{}{
		"model":       cfg.OpenAIModel,
		"messages":    reqMsgs,
		"temperature": cfg.Temperature,
		"stream":      true,
	}

	bodyBytes, _ := json.Marshal(payload)
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(bodyBytes))
	if err != nil {
		errChan <- err
		return
	}
	req.Header.Set("Content-Type", "application/json")
	if cfg.OpenAIAPIKey != "" {
		req.Header.Set("Authorization", "Bearer "+cfg.OpenAIAPIKey)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		errChan <- fmt.Errorf("Failed to connect to API at %s: %v", url, err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		errChan <- fmt.Errorf("OpenAI API Error (%d): %s", resp.StatusCode, string(body))
		return
	}

	scanner := bufio.NewScanner(resp.Body)
	for scanner.Scan() {
		line := scanner.Text()
		if !strings.HasPrefix(line, "data: ") {
			continue
		}
		dataStr := strings.TrimPrefix(line, "data: ")
		if dataStr == "[DONE]" {
			break
		}

		var chunk struct {
			Choices []struct {
				Delta struct {
					Content string `json:"content"`
				} `json:"delta"`
			} `json:"choices"`
		}

		if err := json.Unmarshal([]byte(dataStr), &chunk); err == nil {
			if len(chunk.Choices) > 0 && chunk.Choices[0].Delta.Content != "" {
				tokenChan <- chunk.Choices[0].Delta.Content
			}
		}
	}

	if err := scanner.Err(); err != nil {
		errChan <- err
	} else {
		close(tokenChan)
	}
}
