import { marked } from 'marked';
import hljs from 'highlight.js';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import 'highlight.js/styles/atom-one-dark.css';
import { getIcon } from './icons.js';

// Configure marked with highlight.js syntax highlighting
marked.setOptions({
  gfm: true,
  breaks: true,
  highlight: function (code, lang) {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext';
    return hljs.highlight(code, { language }).value;
  }
});

// Helper function to render math expressions using KaTeX
function renderMath(text) {
  if (!text) return '';

  // Render block math $$ ... $$
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (match, math) => {
    try {
      return `<div class="katex-block">${katex.renderToString(math.trim(), { displayMode: true, throwOnError: false })}</div>`;
    } catch (e) {
      return match;
    }
  });

  // Render inline math $ ... $
  text = text.replace(/\$([^\$\n]+?)\$/g, (match, math) => {
    try {
      return katex.renderToString(math.trim(), { displayMode: false, throwOnError: false });
    } catch (e) {
      return match;
    }
  });

  return text;
}

// Process reasoning model thinking blocks <think>...</think>
function processThinkBlocks(text) {
  if (!text) return { thinking: '', body: '' };

  const thinkRegex = /<think>([\s\S]*?)(?:<\/think>|$)/i;
  const match = text.match(thinkRegex);

  if (match) {
    const thinkingContent = match[1].trim();
    const bodyContent = text.replace(thinkRegex, '').trim();
    return { thinking: thinkingContent, body: bodyContent };
  }

  return { thinking: '', body: text };
}

export function renderMarkdown(rawText, options = { isStreaming: false }) {
  if (!rawText) return '';

  // 1. Separate thinking block if present
  const { thinking, body } = processThinkBlocks(rawText);

  let htmlResult = '';

  // 2. Render Thinking block if present
  if (thinking) {
    const isCompleted = rawText.includes('</think>');
    const thinkingTitle = isCompleted ? '思維鏈 / Reasoning Process' : '正在思考中... / Thinking...';
    htmlResult += `
      <div class="think-block ${isCompleted ? 'collapsed' : ''}">
        <div class="think-header" onclick="this.parentElement.classList.toggle('collapsed')">
          <span style="display:flex;align-items:center;gap:6px;">
            ${getIcon('think')} <strong>${thinkingTitle}</strong>
          </span>
          <span>${getIcon('chevronDown')}</span>
        </div>
        <div class="think-content">${renderMath(thinking)}</div>
      </div>
    `;
  }

  // 3. Render body text markdown
  if (body) {
    let parsedBody = marked.parse(body);
    parsedBody = renderMath(parsedBody);
    htmlResult += `<div class="markdown-body">${parsedBody}</div>`;
  }

  return htmlResult;
}

// Global copy function for code blocks
window.copyCodeBlock = function (buttonElement) {
  const codeBlock = buttonElement.closest('.code-block-wrapper').querySelector('code');
  if (codeBlock) {
    const textToCopy = codeBlock.innerText;
    navigator.clipboard.writeText(textToCopy).then(() => {
      const originalHTML = buttonElement.innerHTML;
      buttonElement.innerHTML = `${getIcon('check')} 已複製!`;
      setTimeout(() => {
        buttonElement.innerHTML = originalHTML;
      }, 2000);
    });
  }
};

// Override marked renderer for code block custom header & copy button
const renderer = new marked.Renderer();
renderer.code = function (code, lang) {
  const language = lang || 'text';
  const highlightedCode = hljs.getLanguage(language)
    ? hljs.highlight(code, { language }).value
    : hljs.highlightAuto(code).value;

  return `
    <div class="code-block-wrapper">
      <div class="code-header">
        <span>${language.toUpperCase()}</span>
        <button class="copy-code-btn" onclick="window.copyCodeBlock(this)">
          ${getIcon('copy')} 複製
        </button>
      </div>
      <pre><code class="hljs ${language}">${highlightedCode}</code></pre>
    </div>
  `;
};

marked.use({ renderer });
