import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { markSkillManualOnly } from "./_frontmatter.mjs";

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
  contents = markSkillManualOnly(contents);
  await writeFile(skillPath, contents);
}

console.log(`Marked ${manualSkills.length} specialist skills as manual-only.`);
