import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const manualSkills = [
  "5-why",
  "add-mcp-server",
  "architecture-diagram",
  "auto-test",
  "caveman-commit",
  "caveman-help",
  "caveman-review",
  "ci-watcher",
  "cmux",
  "compress",
  "db-introspect",
  "file-watcher",
  "frontend-design",
  "presentation-creator",
  "scheduler",
  "self-improve",
  "session-reader",
  "skill-creator",
  "skill-evolution",
  "system-awareness",
  "todo-update",
  "write-todos",
];

for (const name of manualSkills) {
  const skillPath = path.join(root, "skills", name, "SKILL.md");
  let contents = await readFile(skillPath, "utf8");
  if (/^disable-model-invocation:/m.test(contents)) {
    contents = contents.replace(/^disable-model-invocation:.*$/m, "disable-model-invocation: true");
  } else {
    const closing = contents.indexOf("\n---", 4);
    if (closing < 0) throw new Error(`Missing frontmatter in ${skillPath}`);
    contents = `${contents.slice(0, closing)}\ndisable-model-invocation: true${contents.slice(closing)}`;
  }
  await writeFile(skillPath, contents);
}

console.log(`Marked ${manualSkills.length} specialist skills as manual-only.`);
