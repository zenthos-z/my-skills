#!/usr/bin/env node
/**
 * Mermaid Syntax Validator
 *
 * Validates Mermaid diagram syntax using mermaid.parse() with JSDOM.
 * Lightweight alternative to Puppeteer-based validation.
 *
 * Usage:
 *   node validate-mermaid.mjs "flowchart TD\n A --> B"
 *   echo "flowchart TD\n A --> B" | node validate-mermaid.mjs -
 *
 * Output (JSON):
 *   {"valid":true}
 *   {"valid":false,"error":"...","rawError":"..."}
 *
 * Requirements:
 *   npm install mermaid jsdom
 */

import { JSDOM } from 'jsdom';

// Initialize JSDOM environment FIRST
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
  runScripts: 'dangerously'
});

// Set global properties BEFORE importing mermaid
global.window = dom.window;
global.document = dom.window.document;
// Node.js 22+ has read-only navigator, skip it

// Mock DOMPurify with full API BEFORE importing mermaid
const mockDOMPurify = {
  sanitize: (html) => html,
  addHook: () => {},
  removeHook: () => {},
  removeAllHooks: () => {},
  setConfig: () => {},
  clearConfig: () => {},
  isValidAttribute: () => true,
  isSupported: true,
  version: '3.0.0'
};
global.DOMPurify = mockDOMPurify;
dom.window.DOMPurify = mockDOMPurify;

// NOW import mermaid (after globals are set)
const mermaid = (await import('mermaid')).default;

// Initialize mermaid
await mermaid.initialize({
  startOnLoad: false,
  suppressErrors: true,
  securityLevel: 'loose'
});

// Get code from argument
const code = process.argv[2];

if (!code) {
  console.error('Usage: node validate-mermaid.mjs "mermaid code"');
  console.error('   or: echo "code" | node validate-mermaid.mjs -');
  process.exit(1);
}

try {
  // Parse the mermaid code
  const result = await mermaid.parse(code.trim());

  if (result) {
    console.log(JSON.stringify({ valid: true }));
  } else {
    console.log(JSON.stringify({
      valid: false,
      error: 'Parse returned false - unknown error',
      rawError: null
    }));
  }
} catch (err) {
  // Extract clean error message
  let errorMessage = err.message || String(err);

  // Clean up common error message patterns
  errorMessage = errorMessage
    .replace(/^Syntax error in text\s*/i, '')
    .replace(/Line:\s*\d+,?\s*/gi, '')
    .replace(/\s+/g, ' ')
    .trim();

  // Categorize common errors
  let errorType = 'syntax';
  if (errorMessage.includes('Unsupported markdown')) {
    errorType = 'markdown_conflict';
  } else if (errorMessage.includes('undefined')) {
    errorType = 'undefined_reference';
  } else if (errorMessage.includes('expecting')) {
    errorType = 'parse_error';
  }

  console.log(JSON.stringify({
    valid: false,
    error: errorMessage,
    errorType: errorType,
    rawError: err.message
  }));
}
