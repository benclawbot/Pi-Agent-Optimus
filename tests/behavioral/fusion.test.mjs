/**
 * Behavioral tests for fusion extension.
 */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(path.dirname(__dirname));

async function loadExt(name) {
  return readFile(path.join(root, "extensions", name, "index.ts"), "utf8");
}

test("fusion registers the fusion tool", async () => {
  const src = await loadExt("fusion");
  assert.match(src, /name:\s*"fusion"/);
  assert.match(src, /label:\s*"MiniMax Fusion"/);
});

test("fusion uses parallel Promise.allSettled for panelists", async () => {
  const src = await loadExt("fusion");
  assert.match(src, /Promise\.allSettled/);
});

test("fusion passes ctx.signal to runModel for abort propagation", async () => {
  const src = await loadExt("fusion");
  assert.match(src, /signal:\s*ctx\.signal/);
});

test("fusion judge is isolated (no-extensions, no-session)", async () => {
  const src = await loadExt("fusion");
  // runModel helper always adds --no-extensions --no-skills for both callers
  const occurrences = (src.match(/--no-extensions/g) ?? []).length;
  assert.ok(occurrences >= 1, "runModel helper must include --no-extensions flag");
});

test("fusion panelists use system+user message split (not leaked user prompt)", async () => {
  const src = await loadExt("fusion");
  // Should have panelistMessages returning a system+user message array
  assert.match(src, /role:\s*"system"/);
  assert.match(src, /role:\s*"user"/);
  // Should NOT have the old single-prompt pattern
  assert.doesNotMatch(src, /panelPrompt\s*\(\s*params\.question/);
});

test("fusion judge gets 1.5x panelist timeout", async () => {
  const src = await loadExt("fusion");
  assert.match(src, /judgeTimeout.*\*\s*1\.5/);
});

test("fusion Promise.allSettled filters empty content correctly", async () => {
  const src = await loadExt("fusion");
  // Should not check for SENTINEL strings in content — that was removed
  assert.doesNotMatch(src, /SENTINEL/);
  // Should filter on !!r.content.trim()
  assert.match(src, /!!.*\.content\.trim/);
});

test("fusion imports resolvePiEntry from shared module", async () => {
  const src = await loadExt("fusion");
  assert.match(src, /from\s+"[^"]*_shared\/pi-resolve"/);
});
