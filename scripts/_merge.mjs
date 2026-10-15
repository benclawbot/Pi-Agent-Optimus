// Shared deep-merge helper for settings.json scripts.
// Preserve current scalar choices, recursively merge objects, and dedupe
// arrays by value rather than object identity (JSON.parse creates new objects).

function canonical(value) {
  return JSON.stringify(value, (_, element) => {
    if (element && typeof element === "object" && !Array.isArray(element)) {
      return Object.fromEntries(
        Object.entries(element).sort(([left], [right]) => left.localeCompare(right))
      );
    }
    return element;
  });
}

export function merge(defaults, current) {
  if (Array.isArray(defaults) && Array.isArray(current)) {
    const seen = new Set();
    return [...defaults, ...current].filter((entry) => {
      const key = canonical(entry);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
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
