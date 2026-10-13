/** Safely update ONLY the first YAML frontmatter block of a skill. */
export function markSkillManualOnly(contents) {
  const newline = contents.startsWith("---\r\n") ? "\r\n" : "\n";
  if (!contents.startsWith("---" + newline)) {
    throw new Error("Skill must begin with YAML frontmatter");
  }

  const start = ("---" + newline).length;
  const closing = contents.indexOf(newline + "---", start);
  if (closing < 0) {
    throw new Error("Skill frontmatter has no closing fence");
  }
  const afterFence = closing + newline.length + 3;
  if (afterFence < contents.length &&
      !contents.startsWith(newline, afterFence)) {
    throw new Error("Invalid YAML closing fence");
  }
  const header = contents.slice(0, closing);
  const tail = contents.slice(closing);
  const setting = /^disable-model-invocation:[^\r\n]*$/m;
  if (setting.test(header)) {
    return header.replace(setting, "disable-model-invocation: true") + tail;
  }
  return header + newline + "disable-model-invocation: true" + tail;
}
