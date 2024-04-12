// console.log('Preload loaded.');

import { contextBridge, ipcRenderer, shell } from 'electron';
import { Marked } from 'marked';
import { markedHighlight } from "marked-highlight";
import hljs from 'highlight.js';

// Tell marked to use highlight.js for code blocks
const marked = new Marked(
  markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code, lang, info) {
      const language = hljs.getLanguage(lang) ? lang : 'plaintext';
      return hljs.highlight(code, { language }).value;
    }
  })
);

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