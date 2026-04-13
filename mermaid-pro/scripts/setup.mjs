#!/usr/bin/env node

/**
 * mermaid-pro Environment Setup
 *
 * Detects dependencies, auto-installs if missing, and reports capabilities.
 * Output: JSON with readiness status and feature availability.
 *
 * Usage:
 *   node scripts/setup.mjs
 */

import { execSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const scriptsDir = __dirname;
const nodeModulesDir = join(scriptsDir, "node_modules");
const validateScript = join(scriptsDir, "validate-mermaid.mjs");

const REQUIRED_PACKAGES = ["jsdom", "mermaid"];
const OPTIONAL_PACKAGES = ["puppeteer"];
const MIN_NODE_VERSION = 18;

// ── Helpers ──

function getNodeVersion() {
  const match = process.version.match(/^v(\d+)/);
  return match ? parseInt(match[1], 10) : 0;
}

function isPackageInstalled(pkg) {
  return existsSync(join(nodeModulesDir, pkg));
}

function run(cmd) {
  try {
    return execSync(cmd, { encoding: "utf-8", cwd: scriptsDir, stdio: "pipe" });
  } catch {
    return null;
  }
}

function runJson(cmd) {
  const out = run(cmd);
  if (!out) return null;
  try {
    return JSON.parse(out.trim());
  } catch {
    return null;
  }
}

// ── Checks ──

function checkNodeVersion() {
  const version = getNodeVersion();
  if (version < MIN_NODE_VERSION) {
    return {
      ok: false,
      error: `Node.js >= ${MIN_NODE_VERSION} required, found ${process.version}`,
    };
  }
  return { ok: true };
}

function checkDependencies() {
  const missing = REQUIRED_PACKAGES.filter((pkg) => !isPackageInstalled(pkg));
  return { allInstalled: missing.length === 0, missing };
}

function installDependencies() {
  const result = run("npm install --no-audit --no-fund");
  return result !== null;
}

function testValidation() {
  // Use stdin piping to avoid shell escaping issues across platforms
  try {
    const out = execSync(`node "${validateScript}" -`, {
      input: "flowchart TD\n  A --> B",
      encoding: "utf-8",
      cwd: scriptsDir,
      stdio: ["pipe", "pipe", "pipe"],
    });
    const parsed = JSON.parse(out.trim());
    return parsed.valid === true;
  } catch {
    return false;
  }
}

function testExport() {
  // Check puppeteer + chromium are available (don't actually launch browser)
  if (!isPackageInstalled("puppeteer")) return false;
  try {
    // Check multiple possible puppeteer cache locations
    const candidates = [
      process.env.PUPPETEER_CACHE_DIR,
      join(process.env.USERPROFILE || process.env.HOME || "", ".cache", "puppeteer"),
      join(process.env.LOCALAPPDATA || "", ".cache", "puppeteer"),
    ].filter(Boolean);
    return candidates.some((dir) => existsSync(dir));
  } catch {
    return false;
  }
}

// ── Main ──

function main() {
  const result = {
    ready: false,
    features: { validate: false, export: false },
  };

  // 1. Check Node.js version
  const nodeCheck = checkNodeVersion();
  if (!nodeCheck.ok) {
    result.error = nodeCheck.error;
    console.log(JSON.stringify(result, null, 2));
    process.exit(1);
  }

  // 2. Check & install dependencies
  const depCheck = checkDependencies();
  if (!depCheck.allInstalled) {
    console.error(`Installing missing packages: ${depCheck.missing.join(", ")}...`);
    const installed = installDependencies();
    if (!installed) {
      result.error = "npm install failed. Run manually: cd scripts && npm install";
      console.log(JSON.stringify(result, null, 2));
      process.exit(1);
    }
    console.error("Dependencies installed successfully.");
  }

  // 3. Test validation capability
  result.features.validate = testValidation();

  // 4. Test export capability
  result.features.export = testExport();

  // 5. Final readiness
  result.ready = result.features.validate;

  if (!result.ready) {
    result.error =
      "Validation test failed. Try: cd scripts && rm -rf node_modules && npm install";
  }

  // Suppress stderr hints, output only JSON to stdout
  console.log(JSON.stringify(result, null, 2));
  process.exit(result.ready ? 0 : 1);
}

main();
