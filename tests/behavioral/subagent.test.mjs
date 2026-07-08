/**
 * Behavioral tests for subagent extension.
 * Verifies tool registration, parameter schema, and ctx usage via source inspection.
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

test("subagent registers the subagent tool", async () => {
  const src = await loadExt("subagent");
  assert.match(src, /registerTool\s*\(\s*\{/);
  assert.match(src, /name:\s*"subagent"/);
  assert.match(src, /label:\s*"Run Subagent"/);
});

test("subagent passes cwd to child process spawn", async () => {
  const src = await loadExt("subagent");
	// spawn call passes cwd: args.cwd — verified by presence of that exact line
	assert.match(src, /cwd:\s*args\.cwd/);
});

test("subagent defaults model to ctx.model, not hardcoded provider", async () => {
  const src = await loadExt("subagent");
  assert.doesNotMatch(src, /params\.model\s*\|\|\s*"\w+\/\w+"/);
  assert.match(src, /params\.model\s*\|\|\s*ctx\.model/);
});

test("subagent read-only tools exclude bash/edit/write", async () => {
  const src = await loadExt("subagent");
  const readTools = src.match(/READ_HEAVY_TOOLS\s*=\s*"([^"]+)"/)?.[1] ?? "";
  assert.ok(readTools.includes("read"));
  assert.ok(!readTools.includes("bash"), "bash must not be in read-only mode");
  assert.ok(!readTools.includes("edit"), "edit must not be in read-only mode");
  assert.ok(!readTools.includes("write"), "write must not be in read-only mode");
});

test("subagent imports resolvePiEntry from shared module", async () => {
  const src = await loadExt("subagent");
  assert.match(src, /from\s+"[^"]*_shared\/pi-resolve"/);
  assert.doesNotMatch(src, /function\s+resolvePiEntry\s*\(/);
});

test("subagent has ring buffer for stdout truncation (not reactive slice)", async () => {
  const src = await loadExt("subagent");
  // Ring buffer uses shift() to drop oldest entries
  assert.match(src, /\.shift\(\)/);
  // Should NOT have the old buggy pattern: if (stdout.length > X) stdout = stdout.slice()
  assert.doesNotMatch(src, /stdout\.length\s*>\s*\d+\s*\)\s*stdout\s*=\s*stdout\.slice/);
});
