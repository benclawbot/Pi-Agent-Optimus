import { cp, mkdir, readFile, realpath, rename, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const sourceRoot = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const targetRoot = path.resolve(process.argv[2] || path.join(os.homedir(), ".pi", "agent"));
const directories = ["agents", "extensions", "project-template", "scripts", "skills", "templates", "tests"];
const files = [".gitignore", "AGENTS.md", "LICENSE", "README.md", "package.json", "setup.ps1", "setup.sh"];

function merge(defaults, current) {
  if (Array.isArray(defaults) && Array.isArray(current)) return [...new Set([...defaults, ...current])];
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

async function samePath(left, right) {
  try {
    return await realpath(left) === await realpath(right);
  } catch {
    return path.resolve(left) === path.resolve(right);
  }
}

await mkdir(targetRoot, { recursive: true });
for (const directory of directories) {
  const source = path.join(sourceRoot, directory);
  const target = path.join(targetRoot, directory);
  if (!(await samePath(source, target))) await cp(source, target, { recursive: true, force: true });
}
for (const file of files) {
  const source = path.join(sourceRoot, file);
  const target = path.join(targetRoot, file);
  if (!(await samePath(source, target))) await cp(source, target, { force: true });
}

const defaults = JSON.parse(await readFile(path.join(sourceRoot, "settings.json"), "utf8"));
let current = {};
try {
  current = JSON.parse(await readFile(path.join(targetRoot, "settings.json"), "utf8"));
} catch (error) {
  if (error.code !== "ENOENT") throw error;
}
const settingsPath = path.join(targetRoot, "settings.json");
const tempPath = `${settingsPath}.tmp`;
await writeFile(tempPath, `${JSON.stringify(merge(defaults, current), null, 2)}\n`, { mode: 0o600 });
await rename(tempPath, settingsPath);

console.log(`Installed Pi harness into ${targetRoot}`);
