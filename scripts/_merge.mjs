// Shared deep-merge helper for settings.json scripts.
// Arrays dedupe via Set, plain objects recurse, primitives prefer current over defaults.

export function merge(defaults, current) {
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
