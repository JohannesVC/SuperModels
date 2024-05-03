// console.log('Preload loaded.');

import { contextBridge, ipcRenderer, shell } from 'electron';
import { marked } from 'marked';
// import { markedHighlight } from "marked-highlight";
import hljs from 'highlight.js';
import katex from 'katex';

// Set up custom renderer
const renderer = new marked.Renderer();

// Override the code block renderer for syntax highlighting
renderer.code = (code, lang) => {
  const language = hljs.getLanguage(lang) ? lang : 'plaintext';
  return `<pre><code class="hljs ${language}">${hljs.highlight(code, { language }).value}</code></pre>`;
};

// Override the paragraph renderer to include LaTeX rendering
renderer.paragraph = (text) => {
  // Regular expressions for detecting inline and display mode LaTeX
  const inlineRegex = /\$(.+?)\$/g;
  const displayRegex = /\$\$(.+?)\$\$/g;

  // Function to replace LaTeX with rendered HTML using KaTeX
  const replaceWithKatex = (match, expr, displayMode) => {
    try {
      return katex.renderToString(expr, { throwOnError: false, displayMode });
    } catch (error) {
      return `<span class="katex-error">Error rendering LaTeX: ${expr}</span>`;
    }
  };

  // Replace all LaTeX in text
  text = text.replace(displayRegex, (match, expr) => replaceWithKatex(match, expr, true));
  text = text.replace(inlineRegex, (match, expr) => replaceWithKatex(match, expr, false));
  return `<p>${text}</p>`;
};

// Apply custom renderer and highlight.js options to marked
marked.setOptions({
  renderer: renderer,
  highlight: (code, lang) => {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext';
    return hljs.highlight(code, { language }).value;
  },
  langPrefix: 'hljs language-',  // Setting CSS class prefix
});

  marked.setOptions({
    highlight: function(code, lang) {
      const language = hljs.getLanguage(lang) ? lang : 'plaintext';
      return hljs.highlight(code, { language }).value;
    }
  });
  
  contextBridge.exposeInMainWorld('api', {
    markdown: (text) => marked.parse(text),
    runPythonScript: (args) => ipcRenderer.send('run-python-script', args),
    onPythonWrite: (args) => ipcRenderer.on('python-write', args),
    onPythonEnd: () => ipcRenderer.send('python-end'),
    onPythonOutput: (callback) => {
      ipcRenderer.on(`python-output`, (event, data) => {
        callback(data);
      });
    },
    onPythonError: (callback) => ipcRenderer.on('python-error', callback),
    onPythonExit: (callback) => ipcRenderer.on('python-exit', callback),
    openExternal: (url) => shell.openExternal(url),
  });