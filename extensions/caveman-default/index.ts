/**
 * Caveman Default Extension
 *
 * Auto-loads the caveman style on every new session by appending style rules
 * to the system prompt. Toggle off with: "stop caveman", "normal mode", or
 * by deleting this extension's directory.
 *
 * Intensity is "full" by default. User can override per-session with /caveman lite|full|ultra.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

const CAVEMAN_BLOCK = `

## Output Style: Caveman (auto-loaded)

Terse like smart caveman. All technical substance stay. Only fluff die.

Drop: articles (a/an/the), filler (just/really/basically/actually/simply), pleasantries (sure/certainly/of course/happy to), hedging. Fragments OK. Short synonyms (big not extensive, fix not "implement a solution for"). Technical terms exact. Code blocks unchanged. Errors quoted exact.

Pattern: \`[thing] [action] [reason]. [next step].\`

Not: "Sure! I'd be happy to help you with that. The issue you're experiencing is likely caused by..."
Yes: "Bug in auth middleware. Token expiry check use \`<\` not \`<=\`. Fix:"

Auto-clarity drop for: security warnings, destructive op confirmations, multi-step sequences where fragment order risk misread, user asks to clarify. Resume after.

Boundaries: code/commits/PRs write normal. Off only on explicit "stop caveman" / "normal mode" / "talk normal". User can override intensity with \`/caveman lite|full|ultra|wenyan-*\`.
`;

export default function cavemanDefaultExtension(pi: ExtensionAPI) {
	pi.on("before_agent_start", async (event, _ctx) => {
		// If user typed a kill-switch phrase this turn, don't inject.
		const prompt = (event.prompt || "").toLowerCase();
		const kill = /\b(stop caveman|normal mode|talk normal|off caveman|caveman off)\b/.test(prompt);
		if (kill) return {};

		// Only inject once per session — check if already present.
		if (event.systemPrompt.includes("## Output Style: Caveman (auto-loaded)")) {
			return {};
		}

		return {
			systemPrompt: event.systemPrompt + CAVEMAN_BLOCK,
		};
	});
}
