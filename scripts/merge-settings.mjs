import { readFile, rename, writeFile } from "node:fs/promises";

const [defaultsPath, currentPath] = process.argv.slice(2);

if (!defaultsPath || !currentPath) {
  console.error("Usage: node merge-settings.mjs <defaults.json> <current.json>");
  process.exit(2);
}

function merge(defaults, current) {
  if (Array.isArray(defaults) && Array.isArray(current)) {
    return [...new Set([...defaults, ...current])];
  }
  if (
    defaults && current &&
    typeof defaults === "object" && typeof current === "object" &&
    !Array.isArray(defaults) && !Array.isArray(current)
  ) {
    const result = { ...defaults };
    for (const [key, value] of Object.entries(current)) {
      result[key] = key in defaults ? merge(defaults[key], value) : value;
    }
    return result;
  }
  return current ?? defaults;
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
