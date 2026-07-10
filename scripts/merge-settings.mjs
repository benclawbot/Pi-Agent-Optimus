import { readFile, rename, writeFile } from "node:fs/promises";
import { merge } from "./_merge.mjs";

const [defaultsPath, currentPath] = process.argv.slice(2);

if (!defaultsPath || !currentPath) {
  console.error("Usage: node merge-settings.mjs <defaults.json> <current.json>");
  process.exit(2);
}

const defaults = JSON.parse(await readFile(defaultsPath, "utf8"));
let current = {};

try {
  current = JSON.parse(await readFile(currentPath, "utf8"));
} catch (error) {
  if (error.code !== "ENOENT") throw error;
}

const output = `${JSON.stringify(merge(defaults, current), null, 2)}\n`;
const tempPath = `${currentPath}.tmp`;
await writeFile(tempPath, output, { mode: 0o600 });
await rename(tempPath, currentPath);
