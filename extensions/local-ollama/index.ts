import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

const OLLAMA_BASE = "http://localhost:11434";

function fallbackProvider(): Parameters<ExtensionAPI["registerProvider"]>[1] {
	return {
		name: "Local Ollama",
		baseUrl: `${OLLAMA_BASE}/v1`,
		apiKey: "local",
		api: "openai-completions",
		models: [{
			id: "hf.co/unsloth/gemma-4-E2B-it-GGUF:Q4_K_M",
			name: "Gemma 4 2B (Q4)",
			reasoning: false,
			input: ["text"],
			cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
			contextWindow: 131072,
			maxTokens: 4096,
		}],
	};
}

async function fetchOllamaModels(): Promise<Parameters<ExtensionAPI["registerProvider"]>[1] | null> {
	// Best-effort: tolerate ECONNREFUSED silently. Ollama isn't always running.
	try {
		const response = await fetch(`${OLLAMA_BASE}/api/tags`, { signal: AbortSignal.timeout(2000) });
		if (!response.ok) return null;
		const data = await response.json() as { models: Array<{ name: string; size: number }> };
		const models = data.models.map((m) => ({
			id: m.name,
			name: m.name.split("/").pop()?.split(":")[0] ?? m.name,
			reasoning: false,
			input: ["text"] as const,
			cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
			contextWindow: 131072,
			maxTokens: 4096,
		}));
		return {
			name: "Local Ollama",
			baseUrl: `${OLLAMA_BASE}/v1`,
			apiKey: "local",
			api: "openai-completions",
			models,
		};
	} catch {
		// Ollama not running — return fallback so the provider id stays valid.
		return fallbackProvider();
	}
}

export default function (pi: ExtensionAPI) {
	// Register fallback synchronously so the provider id is always present.
	// Refresh with live models asynchronously on a deferred microtask so a
	// ECONNREFUSED never blocks startup or pollutes the console.
	pi.registerProvider("local-ollama", fallbackProvider());
	void Promise.resolve().then(async () => {
		const live = await fetchOllamaModels();
		if (live) pi.registerProvider("local-ollama", live);
	});
}