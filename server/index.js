import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const DEFAULT_PORT = process.env.PORT || 3100;

app.use(cors());
app.use(express.json());

// Serve static compiled web app files if dist exists
app.use(express.static(path.join(__dirname, '../dist')));
app.use(express.static(path.join(__dirname, '../')));

// Health & Ultra-Low Resource Usage Monitor
app.get('/api/health', (req, res) => {
  const memoryUsage = process.memoryUsage();
  res.json({
    status: 'online',
    app: 'ZeroAI Desk Server',
    memory: {
      rssMB: (memoryUsage.rss / 1024 / 1024).toFixed(2),
      heapUsedMB: (memoryUsage.heapUsed / 1024 / 1024).toFixed(2)
    },
    uptimeSeconds: Math.floor(process.uptime())
  });
});

// Proxy Ollama status check
app.get('/api/ollama/status', async (req, res) => {
  try {
    const response = await fetch('http://127.0.0.1:11434/api/tags', {
      signal: AbortSignal.timeout(3000)
    });
    if (response.ok) {
      const data = await response.json();
      return res.json({ connected: true, models: data.models || [] });
    }
  } catch (err) {
    // Ollama not responding
  }
  return res.json({ connected: false, models: [] });
});

// Universal Streaming Chat Proxy for Web Pairing
app.post('/api/chat/stream', async (req, res) => {
  const { provider, model, messages, baseUrl, apiKey, parameters } = req.body;

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  try {
    if (provider === 'ollama') {
      const targetUrl = `${baseUrl || 'http://127.0.0.1:11434'}/api/chat`;
      const response = await fetch(targetUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model,
          messages,
          stream: true,
          options: parameters
        })
      });

      if (!response.ok) {
        res.write(`data: ${JSON.stringify({ error: `Ollama status ${response.status}` })}\n\n`);
        return res.end();
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        res.write(decoder.decode(value, { stream: true }));
      }
      res.end();
    } else {
      // Proxy OpenAI compatible endpoint
      const targetUrl = `${(baseUrl || 'https://api.openai.com').replace(/\/$/, '')}/v1/chat/completions`;
      const headers = { 'Content-Type': 'application/json' };
      if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;

      const response = await fetch(targetUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          model,
          messages,
          temperature: parseFloat(parameters?.temperature || 0.7),
          stream: true
        })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        res.write(decoder.decode(value, { stream: true }));
      }
      res.end();
    }
  } catch (err) {
    res.write(`data: ${JSON.stringify({ error: err.message })}\n\n`);
    res.end();
  }
});

function startServer(port) {
  const server = app.listen(port, () => {
    console.log(`\n==================================================`);
    console.log(`🚀 ZeroAI Desk Web Server Running at: http://localhost:${port}`);
    console.log(`==================================================\n`);
  });

  server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      console.log(`ℹ Port ${port} is already in use. Server is already running on this system.`);
      // Exit gracefully without uncaught exception popup
      process.exit(0);
    } else {
      console.error('Server error:', err);
    }
  });
}

startServer(DEFAULT_PORT);
