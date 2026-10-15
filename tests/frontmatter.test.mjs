import assert from "node:assert/strict";
import test from "node:test";
import { markSkillManualOnly } from "../scripts/_frontmatter.mjs";

test("adds flag only within opening YAML frontmatter", () => {
  const input = "---\nname: demo\ndescription: demo\n---\n\n# Body\n\n---\nOther text\n";
  const actual = markSkillManualOnly(input);
  assert.equal(actual, "---\nname: demo\ndescription: demo\ndisable-model-invocation: true\n---\n\n# Body\n\n---\nOther text\n");
});

test("replaces an existing frontmatter flag and leaves body unchanged", () => {
  const input = "---\nname: demo\ndisable-model-invocation: false\n---\n\ndisable-model-invocation: false\n";
  assert.equal(markSkillManualOnly(input), "---\nname: demo\ndisable-model-invocation: true\n---\n\ndisable-model-invocation: false\n");
});

test("frontmatter update is idempotent", () => {
  const input = "---\nname: demo\n---\n";
  const updated = markSkillManualOnly(input);
  assert.equal(markSkillManualOnly(updated), updated);
});

test("rejects malformed frontmatter instead of rewriting the body", () => {
  assert.throws(() => markSkillManualOnly("no frontmatter\n---"), /begin/);
  assert.throws(() => markSkillManualOnly("---\nname: demo\n"), /closing/);
  assert.throws(() => markSkillManualOnly("---\nname: demo\n--- trailing\n"), /closing/);
});

test("preserves Windows newline conventions", () => {
  const input = "---\r\nname: demo\r\n---\r\n# Body\r\n";
  assert.equal(markSkillManualOnly(input), "---\r\nname: demo\r\ndisable-model-invocation: true\r\n---\r\n# Body\r\n");
});
