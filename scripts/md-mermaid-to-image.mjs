#!/usr/bin/env node
/**
 * Markdown Mermaid to Image Converter
 *
 * Scans markdown files, extracts mermaid code blocks, converts them to images,
 * and replaces the code blocks with image references.
 *
 * Usage:
 *   node md-mermaid-to-image.mjs <file.md|directory> [options]
 *
 * Options:
 *   --format <png|svg>   Output format (default: svg)
 *   --keep-code          Keep original mermaid code block below image
 *   --prefix <name>      Image filename prefix (default: mermaid-)
 *   --dry-run            Show what would be done without making changes
 *
 * Requirements:
 *   npm install puppeteer mermaid
 *
 * Example:
 *   node md-mermaid-to-image.mjs ./docs --format svg
 *   node md-mermaid-to-image.mjs README.md --keep-code
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import puppeteer from 'puppeteer';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Parse arguments
const args = process.argv.slice(2);
if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
  console.log(`
Markdown Mermaid to Image Converter

Usage:
  node md-mermaid-to-image.mjs <file.md|directory> [options]

Options:
  --format <png|svg>   Output format (default: svg)
  --keep-code          Keep original mermaid code block below image
  --prefix <name>      Image filename prefix (default: mermaid-)
  --dry-run            Show what would be done without making changes
  --help, -h           Show this help message

Examples:
  node md-mermaid-to-image.mjs ./docs
  node md-mermaid-to-image.mjs README.md --format svg --keep-code
`);
  process.exit(0);
}

// Parse options
let targetPath = '';
let format = 'svg';
let keepCode = false;
let prefix = 'mermaid-';
let dryRun = false;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--format') {
    format = args[++i];
  } else if (args[i] === '--keep-code') {
    keepCode = true;
  } else if (args[i] === '--prefix') {
    prefix = args[++i];
  } else if (args[i] === '--dry-run') {
    dryRun = true;
  } else if (!args[i].startsWith('--')) {
    targetPath = args[i];
  }
}

if (!targetPath) {
  console.error('Error: No file or directory specified');
  process.exit(1);
}

// Find markdown files
function findMarkdownFiles(target) {
  const stat = fs.statSync(target);
  if (stat.isFile()) {
    return [target];
  }
  if (stat.isDirectory()) {
    const files = [];
    const entries = fs.readdirSync(target, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.isDirectory() && !entry.name.startsWith('.') && entry.name !== 'node_modules') {
        files.push(...findMarkdownFiles(path.join(target, entry.name)));
      } else if (entry.isFile() && entry.name.endsWith('.md')) {
        files.push(path.join(target, entry.name));
      }
    }
    return files;
  }
  return [];
}

// Extract mermaid blocks from markdown content
function extractMermaidBlocks(content) {
  const regex = /```mermaid\n([\s\S]*?)```/g;
  const blocks = [];
  let match;
  while ((match = regex.exec(content)) !== null) {
    blocks.push({
      fullMatch: match[0],
      code: match[1].trim(),
      startIndex: match.index,
      endIndex: match.index + match[0].length
    });
  }
  return blocks;
}

// Generate unique filename for image
function generateImageFilename(index, code) {
  const hash = code.slice(0, 50).replace(/[^a-zA-Z0-9]/g, '-').slice(0, 20);
  return `${prefix}${index + 1}-${hash}.${format}`;
}

// HTML template for rendering mermaid
const htmlTemplate = (code) => `
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
  <style>
    body { margin: 0; padding: 20px; background: transparent; }
    .mermaid { display: flex; justify-content: center; }
  </style>
</head>
<body>
  <div class="mermaid">${code}</div>
  <script>
    mermaid.initialize({ startOnLoad: true, theme: 'default' });
  </script>
</body>
</html>
`;

// Convert mermaid code to image using puppeteer
async function convertToImage(browser, code, outputPath, outputFormat) {
  let page;
  try {
    page = await browser.newPage();
    await page.setContent(htmlTemplate(code), { waitUntil: 'networkidle0' });

    // Wait for mermaid to render
    await page.waitForSelector('.mermaid svg', { timeout: 10000 });

    const svgElement = await page.$('.mermaid svg');
    if (!svgElement) {
      throw new Error('SVG element not found');
    }

    if (outputFormat === 'svg') {
      const svgContent = await page.evaluate(el => el.outerHTML, svgElement);
      fs.writeFileSync(outputPath, svgContent);
    } else {
      // PNG screenshot
      await svgElement.screenshot({
        path: outputPath,
        omitBackground: true
      });
    }
    return true;
  } catch (err) {
    console.error(`  Failed to convert: ${err.message}`);
    return false;
  } finally {
    if (page) await page.close();
  }
}

// Process a single markdown file
async function processMarkdownFile(browser, mdFilePath) {
  console.log(`\n📄 Processing: ${mdFilePath}`);

  const content = fs.readFileSync(mdFilePath, 'utf-8');
  const blocks = extractMermaidBlocks(content);

  if (blocks.length === 0) {
    console.log('  No mermaid blocks found.');
    return { processed: 0, converted: 0 };
  }

  console.log(`  Found ${blocks.length} mermaid block(s)`);

  const mdDir = path.dirname(mdFilePath);
  const conversions = [];

  // Process blocks in reverse order to maintain correct indices
  for (let i = blocks.length - 1; i >= 0; i--) {
    const block = blocks[i];
    const imageFilename = generateImageFilename(i, block.code);
    const imagePath = path.join(mdDir, imageFilename);

    if (dryRun) {
      console.log(`  [DRY-RUN] Would create: ${imageFilename}`);
      conversions.push({
        block,
        imageFilename,
        imagePath,
        startIndex: block.startIndex,
        endIndex: block.endIndex
      });
    } else {
      console.log(`  Converting to: ${imageFilename}`);
      const success = await convertToImage(browser, block.code, imagePath, format);
      if (success) {
        conversions.push({
          block,
          imageFilename,
          imagePath,
          startIndex: block.startIndex,
          endIndex: block.endIndex
        });
      }
    }
  }

  // Replace blocks with images
  if (!dryRun && conversions.length > 0) {
    let newContent = content;
    // Sort by startIndex descending to replace from end
    conversions.sort((a, b) => b.startIndex - a.startIndex);

    for (const { block, imageFilename, startIndex, endIndex } of conversions) {
      const imageRef = `![${imageFilename}](${imageFilename})`;
      const replacement = keepCode
        ? `${imageRef}\n\n<details>\n<summary>Mermaid Code</summary>\n\n\`\`\`mermaid\n${block.code}\n\`\`\`\n\n</details>`
        : imageRef;
      newContent = newContent.slice(0, startIndex) + replacement + newContent.slice(endIndex);
    }

    fs.writeFileSync(mdFilePath, newContent);
    console.log(`  ✅ Updated: ${mdFilePath}`);
  }

  return { processed: blocks.length, converted: conversions.length };
}

// Main
async function main() {
  const mdFiles = findMarkdownFiles(targetPath);
  console.log(`Found ${mdFiles.length} markdown file(s)`);

  if (mdFiles.length === 0) {
    return;
  }

  // Launch browser (only if not dry-run)
  let browser = null;
  if (!dryRun) {
    console.log('Launching browser...');
    browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
  }

  try {
    let totalProcessed = 0;
    let totalConverted = 0;

    for (const file of mdFiles) {
      const result = await processMarkdownFile(browser, file);
      totalProcessed += result.processed;
      totalConverted += result.converted;
    }

    console.log(`\n📊 Summary:`);
    console.log(`   Files processed: ${mdFiles.length}`);
    console.log(`   Mermaid blocks found: ${totalProcessed}`);
    if (dryRun) {
      console.log(`   [DRY-RUN] No changes made`);
    } else {
      console.log(`   Images generated: ${totalConverted}`);
    }
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

main().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
