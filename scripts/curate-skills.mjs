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
  // Find the FIRST horizontal rule after the opening fence. The frontmatter is
  // delimited by `---` on its own line; later `---` blocks inside the body must
  // not be matched (the previous indexOf heuristic broke on body HRs).
  const openEnd = contents.indexOf("\n---", 0);
  if (openEnd < 0) throw new Error(`Missing frontmatter in ${skillPath}`);
  const headerStart = openEnd + 1;
  const headerEnd = contents.indexOf("\n---", headerStart + 4);
  if (headerEnd < 0) throw new Error(`Missing frontmatter in ${skillPath}`);
  const header = contents.slice(0, headerEnd);
  const body = contents.slice(headerEnd);
  if (/^disable-model-invocation:/m.test(header)) {
    contents = header.replace(/^disable-model-invocation:.*$/m, "disable-model-invocation: true") + body;
  } else {
    contents = `${header}\ndisable-model-invocation: true\n${body}`;
  }
  await writeFile(skillPath, contents);
}

console.log(`Marked ${manualSkills.length} specialist skills as manual-only.`);
