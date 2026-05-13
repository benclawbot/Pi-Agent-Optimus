/**
 * Loop Detection Extension
 *
 * Detects when the same command is repeatedly invoked with identical outcomes,
 * and responds with appropriate escalation to break repetitive loops.
 *
 * Usage:
 *   Automatically loaded — no user action required
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

interface LoopEntry {
	command: string;
	outcome: string;
	timestamp: number;
	count: number;
}

interface LoopConfig {
	enabled: boolean;
	maxRepeats: number;
	timeWindowMs: number;
}

const DEFAULT_CONFIG: LoopConfig = {
	enabled: true,
	maxRepeats: 3,
	timeWindowMs: 10000, // 10 seconds
};

function getConfig(pi: ExtensionAPI): LoopConfig {
	const userConfig = pi.getConfig<LoopConfig>("loopDetection");
	return { ...DEFAULT_CONFIG, ...userConfig };
}

export default function loopDetectionExtension(pi: ExtensionAPI) {
	const history: LoopEntry[] = [];
	const MAX_HISTORY = 20;

	function cleanHistory(): void {
		const config = getConfig(pi);
		const cutoff = Date.now() - config.timeWindowMs;
		// Remove entries outside time window
		while (history.length > 0 && history[0].timestamp < cutoff) {
			history.shift();
		}
		// Also cap history size
		while (history.length > MAX_HISTORY) {
			history.shift();
		}
	}

	function findOrCreate(command: string, outcome: string): LoopEntry {
		cleanHistory();
		// Find existing entry for same command+outcome
		for (const entry of history) {
			if (entry.command === command && entry.outcome === outcome) {
				return entry;
			}
		}
		// Create new entry
		const entry: LoopEntry = {
			command,
			outcome,
			timestamp: Date.now(),
			count: 0,
		};
		history.push(entry);
		return entry;
	}

	function getLoopCount(command: string, outcome: string): number {
		cleanHistory();
		let maxCount = 0;
		for (const entry of history) {
			if (entry.command === command && entry.outcome === outcome) {
				maxCount = Math.max(maxCount, entry.count);
			}
		}
		return maxCount;
	}

	// Intercept input to detect loops BEFORE command execution
	pi.on("input", async (event, ctx) => {
		const config = getConfig(pi);
		if (!config.enabled) return;

		const text = event.text?.trim();
		if (!text || !text.startsWith("/")) return;

		// We'll track outcomes AFTER command execution via a turn_end listener
		// For now, detect rapid repetition from history

		cleanHistory();
		const recentSame = history.filter(
			(e) => e.command === text && Date.now() - e.timestamp < config.timeWindowMs
		);

		if (recentSame.length >= config.maxRepeats) {
			const totalRecent = recentSame.reduce((sum, e) => sum + e.count, 0) + 1;
			if (totalRecent >= config.maxRepeats * 2) {
				// Very stuck loop - provide a strongly worded response
				ctx.ui.notify(
					`Loops detected: /${text.slice(1)} repeated ${totalRecent}+ times with same result. Use /new or change context.`,
					"warning",
					{ duration: 4000 }
				);
			}
		}
	});

	// Track command outcomes on turn end
	pi.on("turn_end", async (event, ctx) => {
		const config = getConfig(pi);
		if (!config.enabled) return;

		// Get the user's command from the last user message
		const entries = ctx.sessionManager.getEntries();
		let lastUserCommand = "";

		for (let i = entries.length - 1; i >= 0; i--) {
			const entry = entries[i];
			if (entry.type === "message" && entry.message.role === "user") {
				const content = entry.message.content;
				if (Array.isArray(content)) {
					for (const c of content) {
						if (c.type === "text") {
							lastUserCommand = c.text.trim();
							break;
						}
					}
				}
				if (lastUserCommand.startsWith("/")) break;
			}
		}

		if (!lastUserCommand.startsWith("/")) return;

		// Get the assistant's response outcome
		let outcome = "";
		const lastMsg = event.message;
		if (lastMsg.role === "assistant") {
			const content = lastMsg.content;
			if (Array.isArray(content)) {
				for (const c of content) {
					if (c.type === "text") {
						outcome = c.text.trim().substring(0, 100); // Normalize length
						break;
					}
				}
			}
		}

		if (!outcome) return;

		// Update or create entry
		const entry = findOrCreate(lastUserCommand, outcome);
		entry.count++;
		entry.timestamp = Date.now();
	});

	// Expose loop status via command
	pi.registerCommand("loop-status", {
		description: "Show command loop detection status",
		handler: async (_args, ctx) => {
			cleanHistory();
			if (history.length === 0) {
				ctx.ui.notify("No command history yet", "info");
				return;
			}

			const lines = history
				.filter((e) => e.count > 0)
				.map((e) => `${e.command}: ${e.count}x (${e.outcome.substring(0, 40)}...)`)
				.slice(-5);

			if (lines.length === 0) {
				ctx.ui.notify("No repeated commands yet", "info");
			} else {
				ctx.ui.notify(lines.join("\n"), "info", { duration: 3000 });
			}
		},
	});

	// Reset loop history
	pi.registerCommand("loop-reset", {
		description: "Reset command loop detection history",
		handler: async (_args, ctx) => {
			history.length = 0;
			ctx.ui.notify("Loop history reset", "info");
		},
	});
}