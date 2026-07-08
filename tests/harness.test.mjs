import assert from "node:assert/strict";
import { access, mkdtemp, readFile, readdir, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

async function source(relativePath) {
  return readFile(path.join(root, relativePath), "utf8");
}

test("read-only subagents cannot invoke a general-purpose shell", async () => {
  const subagent = await source("extensions/subagent/index.ts");
  const tools = subagent.match(/const READ_HEAVY_TOOLS = "([^"]+)"/)?.[1].split(",") ?? [];

  assert.ok(tools.includes("read"));
  assert.ok(!tools.includes("bash"), "read mode must not expose bash");
  assert.ok(!tools.includes("edit"), "read mode must not expose edit");
  assert.ok(!tools.includes("write"), "read mode must not expose write");
});

test("subagents default to the current parent model", async () => {
  const subagent = await source("extensions/subagent/index.ts");

  assert.match(subagent, /async execute\([^)]*ctx\)/);
  assert.match(subagent, /params\.model \|\| ctx\.model\?\.id/);
  assert.doesNotMatch(subagent, /params\.model \|\| "minimax\//);
});

test("the distributable settings keep the active package and extensions", async () => {
  const settings = JSON.parse(await source("settings.json"));

  assert.ok(settings.packages?.includes("npm:context-mode"));
  assert.ok(settings.extensions?.includes("+extensions/subagent/index.ts"));
  assert.ok(settings.extensions?.includes("+extensions/repo-map/index.ts"));
});

test("settings installation merges resources without replacing user defaults", async () => {
  const temp = await mkdtemp(path.join(os.tmpdir(), "pi-settings-"));
  const defaultsPath = path.join(temp, "defaults.json");
  const currentPath = path.join(temp, "current.json");

  await writeFile(defaultsPath, JSON.stringify({
    defaultModel: "distribution-default",
    extensions: ["a", "b"],
    packages: ["context-mode"],
    compaction: { enabled: true, reserveTokens: 8192 },
  }));
  await writeFile(currentPath, JSON.stringify({
    defaultModel: "user-choice",
    extensions: ["b", "custom"],
    compaction: { reserveTokens: 12000 },
  }));

  const result = spawnSync(process.execPath, [
    path.join(root, "scripts", "merge-settings.mjs"),
    defaultsPath,
    currentPath,
  ], { encoding: "utf8" });

  assert.equal(result.status, 0, result.stderr);
  const merged = JSON.parse(await readFile(currentPath, "utf8"));
  assert.equal(merged.defaultModel, "user-choice");
  assert.deepEqual(merged.extensions, ["a", "b", "custom"]);
  assert.deepEqual(merged.packages, ["context-mode"]);
  assert.deepEqual(merged.compaction, { enabled: true, reserveTokens: 12000 });
});

test("todo panel stays visible and exposes a refresh command", async () => {
  const panel = await source("extensions/todo-panel/index.ts");

  assert.doesNotMatch(panel, /if \(stats\.total === 0\) return \[\]/);
  assert.match(panel, /pi\.registerCommand\("todo-panel"/);
  assert.match(panel, /ctx\.ui\.setWidget\("todo-panel"/);
  assert.match(panel, /ui\.notify\(`Todo panel failed:/);
});

test("specialist skills are hidden from the default model prompt", async () => {
  for (const name of ["architecture-diagram", "db-introspect", "presentation-creator", "scheduler"]) {
    const skill = await source(`skills/${name}/SKILL.md`);
    assert.match(skill, /^disable-model-invocation: true$/m, `${name} should remain manually invokable`);
  }
});

test("agent instructions enforce the error-prevention protocol", async () => {
  const agents = await source("AGENTS.md");
  const verifyDone = await source("skills/verify-done/SKILL.md");

  assert.match(agents, /requirements ledger/i);
  assert.match(agents, /Absence of evidence is not evidence of absence/i);
  assert.match(agents, /cheapest decisive check/i);
  assert.match(agents, /do not repeat the same failed action unchanged/i);
  assert.match(agents, /never simulate a tool action/i);
  assert.match(agents, /open, parse, or run at the expected path/i);
  assert.match(verifyDone, /Re-check every item in the requirements ledger/i);
  assert.match(verifyDone, /Verify requested artifacts exist at the expected paths/i);
});

test("Telegram bridge is enabled and guarded by a single-instance lock", async () => {
  const settings = JSON.parse(await source("settings.json"));
  const telegram = await source("extensions/telegram/index.ts");

  assert.ok(settings.extensions?.includes("+extensions/telegram/index.ts"));
  assert.match(telegram, /openSync\(lockPath, "wx"\)/);
  assert.match(telegram, /allowedUsers\.includes/);
  assert.match(telegram, /renameSync\(tempPath, configPath\)/);
  assert.doesNotMatch(telegram, /let .*ctx|captured.*ctx/i);
});

test("every configured local extension exists", async () => {
  const settings = JSON.parse(await source("settings.json"));

  for (const configured of settings.extensions ?? []) {
    if (!configured.startsWith("+extensions/")) continue;
    await access(path.join(root, configured.slice(1)));
  }
});

test("sensitive runtime files cannot be committed", async () => {
  const ignore = await source(".gitignore");

  for (const sensitive of ["auth.json", "trust.json", "npm/", "sessions/"]) {
    assert.match(ignore, new RegExp(`^${sensitive.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`, "m"));
  }
});

test("all local skills have valid frontmatter", async () => {
  const skillsDir = path.join(root, "skills");
  for (const entry of await readdir(skillsDir, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const skill = await readFile(path.join(skillsDir, entry.name, "SKILL.md"), "utf8");
    assert.match(skill, /^---\r?\n/);
    assert.match(skill, /^name:\s*\S+/m);
    assert.match(skill, /^description:\s*\S+/m);
    const description = skill.match(/^description:\s*(.+)$/m)?.[1] ?? "";
    if (!/^['"]/.test(description)) {
      assert.doesNotMatch(description, /:\s/, `${entry.name} description must quote YAML-significant colons`);
    }
  }
});

test("installer reproduces the harness without replacing user settings", async () => {
  const temp = await mkdtemp(path.join(os.tmpdir(), "pi-harness-"));
  await writeFile(path.join(temp, "settings.json"), JSON.stringify({
    defaultModel: "user-model",
    extensions: ["+extensions/user-only/index.ts"],
  }));
  await writeFile(path.join(temp, "auth.json"), "keep-me");

  const result = spawnSync(process.execPath, [path.join(root, "scripts", "install-harness.mjs"), temp], {
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stderr);

  const installed = JSON.parse(await readFile(path.join(temp, "settings.json"), "utf8"));
  assert.equal(installed.defaultModel, "user-model");
  assert.ok(installed.extensions.includes("+extensions/telegram/index.ts"));
  assert.ok(installed.extensions.includes("+extensions/user-only/index.ts"));
  assert.equal(await readFile(path.join(temp, "auth.json"), "utf8"), "keep-me");
  await access(path.join(temp, "extensions", "todo-panel", "index.ts"));
  await access(path.join(temp, "tests", "harness.test.mjs"));
});

test("fusion uses parallel MiniMax panelists and an M3 judge", async () => {
  const settings = JSON.parse(await source("settings.json"));
  const fusion = await source("extensions/fusion/index.ts");

  assert.ok(settings.extensions?.includes("+extensions/fusion/index.ts"));
  assert.match(fusion, /Promise\.allSettled/);
  assert.match(fusion, /minimax\/MiniMax-M2\.7/);
  assert.match(fusion, /minimax\/MiniMax-M3/);
  assert.match(fusion, /profile.*lite/);
  assert.match(fusion, /FULL_PANEL/);
  assert.match(fusion, /--no-extensions/);
  assert.match(fusion, /consensus/i);
  assert.match(fusion, /contradictions/i);
  assert.match(fusion, /blind spots/i);
});
