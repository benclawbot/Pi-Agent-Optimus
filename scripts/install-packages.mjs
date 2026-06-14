import { spawnSync } from "node:child_process";
import { readFile } from "node:fs/promises";

const [settingsPath] = process.argv.slice(2);
if (!settingsPath) {
  console.error("Usage: node install-packages.mjs <settings.json>");
  process.exit(2);
}

const settings = JSON.parse(await readFile(settingsPath, "utf8"));
for (const entry of settings.packages ?? []) {
  const source = typeof entry === "string" ? entry : entry.source;
  if (!source) continue;

  console.log(`Installing ${source}...`);
  const result = spawnSync("pi", ["install", source], {
    shell: process.platform === "win32",
    stdio: "inherit",
  });
  if (result.status !== 0) process.exit(result.status ?? 1);
}
