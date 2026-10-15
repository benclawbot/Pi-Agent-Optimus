/**
 * Exercise a fresh Pi harness installation in a disposable directory.
 * No global Pi executable, external network access, or real ~/.pi files.
 */
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { access, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const home = await mkdtemp(path.join(os.tmpdir(), "pi-fresh-install-check-"));
const target = path.join(home, ".pi", "agent");

function run(command, args) {
  const result = spawnSync(command, args, {
    cwd: root,
    stdio: "inherit",
    shell: process.platform === "win32" && command === "npm",
    timeout: 120000,
  });
  assert.equal(result.status, 0,
    command + " " + args.join(" ") + " failed (signal=" + result.signal
    + ", error=" + result.error + ")");
}

try {
  run(process.execPath, ["scripts/install-harness.mjs", target]);
  await access(path.join(target, "extensions", "todos", "index.ts"));
  await access(path.join(target, "tests", "harness.test.mjs"));
  run("npm", ["--prefix", target, "test"]);

  const userSettings = {
    defaultModel: "user-choice-must-survive",
    extensions: ["+extensions/user-only/index.ts"],
    retry: { maxRetries: 1 },
  };
  await writeFile(path.join(target, "settings.json"),
    JSON.stringify(userSettings), { mode: 0o600 });
  await writeFile(path.join(target, "auth.json"), "local-secret-remains-local",
    { mode: 0o600 });

  run(process.execPath, ["scripts/install-harness.mjs", target]);
  const installed = JSON.parse(await readFile(path.join(target, "settings.json"), "utf8"));
  assert.equal(installed.defaultModel, userSettings.defaultModel);
  assert.equal(installed.retry.maxRetries, 1);
  assert.ok(installed.extensions.includes("+extensions/user-only/index.ts"));
  assert.ok(installed.extensions.includes("+extensions/todos/index.ts"));
  assert.equal(await readFile(path.join(target, "auth.json"), "utf8"),
    "local-secret-remains-local");
  assert.equal(new Set(installed.extensions).size, installed.extensions.length);

  run(process.execPath, ["scripts/install-harness.mjs", target]);
  assert.deepEqual(JSON.parse(await readFile(path.join(target, "settings.json"), "utf8")),
    installed);
  console.log("Fresh install, in-place upgrade and idempotence verified.");
} finally {
  await rm(home, { recursive: true, force: true });
}
