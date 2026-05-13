import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

export default async function (pi: ExtensionAPI) {
  // Fetch available models from Ollama
  try {
    const response = await fetch("http://localhost:11434/api/tags");
    if (response.ok) {
      const data = await response.json() as { models: Array<{ name: string; size: number }> };
      const models = data.models.map((m) => ({
        id: m.name,
        name: m.name.split("/").pop()?.split(":")[0] ?? m.name,
        reasoning: false,
        input: ["text"] as const,
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
        contextWindow: 131072,
        maxTokens: 4096
      }));

      pi.registerProvider("local-ollama", {
        name: "Local Ollama",
        baseUrl: "http://localhost:11434/v1",
        apiKey: "local",
        api: "openai-completions",
        models
      });
    }
  } catch (e) {
    console.error("Failed to fetch Ollama models:", e);
    // Register fallback
    pi.registerProvider("local-ollama", {
      name: "Local Ollama",
      baseUrl: "http://localhost:11434/v1",
      apiKey: "local",
      api: "openai-completions",
      models: [{
        id: "hf.co/unsloth/gemma-4-E2B-it-GGUF:Q4_K_M",
        name: "Gemma 4 2B (Q4)",
        reasoning: false,
        input: ["text"],
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
        contextWindow: 131072,
        maxTokens: 4096
      }]
    });
  }
}