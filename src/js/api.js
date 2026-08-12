// Unified Multi-Model API Client (Local Ollama & Remote APIs)

export class AIEngine {
  constructor() {
    this.settings = {
      provider: 'ollama', // 'ollama' | 'openai' | 'anthropic' | 'gemini' | 'deepseek' | 'custom'
      model: 'llama3.2',
      baseUrl: 'http://127.0.0.1:11434',
      apiKey: '',
      parameters: {
        temperature: 0.7,
        top_p: 0.9,
        max_tokens: 4096,
        repeat_penalty: 1.1,
        frequency_penalty: 0.0,
        presence_penalty: 0.0,
        systemPrompt: 'You are a helpful, intelligent, and precise AI assistant.'
      }
    };
  }

  updateSettings(newSettings) {
    this.settings = {
      ...this.settings,
      ...newSettings,
      parameters: {
        ...this.settings.parameters,
        ...(newSettings.parameters || {})
      }
    };
  }

  // Stream chat response token by token
  async streamChat(messages, onChunk, onError, signal) {
    const { provider, model, baseUrl, apiKey, parameters } = this.settings;

    try {
      if (provider === 'ollama') {
        await this._streamOllama(messages, onChunk, signal);
      } else if (provider === 'anthropic') {
        await this._streamAnthropic(messages, onChunk, signal);
      } else {
        // Default OpenAI-compatible stream (OpenAI, DeepSeek, Gemini-Proxy, Custom)
        await this._streamOpenAICompatible(messages, onChunk, signal);
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('Stream generation aborted by user.');
        return;
      }
      console.error(`API Stream Error (${provider}):`, err);
      if (onError) onError(err);
    }
  }

  // Local Ollama streaming endpoint
  async _streamOllama(messages, onChunk, signal) {
    const { model, baseUrl, parameters } = this.settings;

    const formattedMessages = [];
    if (parameters.systemPrompt) {
      formattedMessages.push({ role: 'system', content: parameters.systemPrompt });
    }
    formattedMessages.push(...messages);

    const response = await fetch(`${baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: model,
        messages: formattedMessages,
        stream: true,
        options: {
          temperature: parseFloat(parameters.temperature),
          top_p: parseFloat(parameters.top_p),
          num_predict: parseInt(parameters.max_tokens),
          repeat_penalty: parseFloat(parameters.repeat_penalty)
        }
      }),
      signal
    });

    if (!response.ok) {
      throw new Error(`Ollama server returned error status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const lines = decoder.decode(value, { stream: true }).split('\n');
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const json = JSON.parse(line);
          if (json.message && json.message.content) {
            onChunk(json.message.content);
          }
        } catch (e) {
          // ignore incomplete JSON chunk
        }
      }
    }
  }

  // Remote OpenAI-Compatible streaming endpoint (OpenAI, DeepSeek, Groq, OpenRouter, Custom)
  async _streamOpenAICompatible(messages, onChunk, signal) {
    const { model, baseUrl, apiKey, parameters } = this.settings;

    const formattedMessages = [];
    if (parameters.systemPrompt) {
      formattedMessages.push({ role: 'system', content: parameters.systemPrompt });
    }
    formattedMessages.push(...messages);

    const endpoint = baseUrl.endsWith('/v1') || baseUrl.endsWith('/v1/')
      ? `${baseUrl.replace(/\/$/, '')}/chat/completions`
      : `${baseUrl.replace(/\/$/, '')}/v1/chat/completions`;

    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) {
      headers['Authorization'] = `Bearer ${apiKey}`;
    }

    const response = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        model: model,
        messages: formattedMessages,
        temperature: parseFloat(parameters.temperature),
        top_p: parseFloat(parameters.top_p),
        max_tokens: parseInt(parameters.max_tokens),
        frequency_penalty: parseFloat(parameters.frequency_penalty),
        presence_penalty: parseFloat(parameters.presence_penalty),
        stream: true
      }),
      signal
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error (${response.status}): ${errorText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const lines = decoder.decode(value, { stream: true }).split('\n');
      for (const line of lines) {
        let trimmed = line.trim();
        if (trimmed.startsWith('data: ')) {
          trimmed = trimmed.substring(6);
        }
        if (trimmed === '[DONE]') break;
        if (!trimmed) continue;

        try {
          const json = JSON.parse(trimmed);
          const delta = json.choices?.[0]?.delta;
          if (delta) {
            // Support DeepSeek R1 reasoning content if available
            if (delta.reasoning_content) {
              onChunk(`<think>${delta.reasoning_content}</think>`);
            }
            if (delta.content) {
              onChunk(delta.content);
            }
          }
        } catch (e) {
          // JSON chunk incomplete
        }
      }
    }
  }

  // Remote Anthropic Claude streaming endpoint
  async _streamAnthropic(messages, onChunk, signal) {
    const { model, apiKey, parameters } = this.settings;

    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: model,
        system: parameters.systemPrompt,
        messages: messages,
        max_tokens: parseInt(parameters.max_tokens),
        temperature: parseFloat(parameters.temperature),
        stream: true
      }),
      signal
    });

    if (!response.ok) {
      throw new Error(`Anthropic API Error (${response.status})`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const lines = decoder.decode(value, { stream: true }).split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.substring(6);
          try {
            const data = JSON.parse(dataStr);
            if (data.type === 'content_block_delta' && data.delta?.text) {
              onChunk(data.delta.text);
            }
          } catch (e) {}
        }
      }
    }
  }
}
