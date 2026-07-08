/**
 * Reload Extension
 *
 * Provides a LLM-callable tool to trigger /reload without requiring
 * the user to manually execute the command.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

export default function reloadExtension(pi: ExtensionAPI) {
	// Register a tool that triggers reload
	pi.registerTool({
		name: "pi_reload",
		label: "Reload",
		description: "Reload pi extensions, skills, prompts, and themes. Use when configuration changes need to take effect.",
		parameters: {
			type: "object",
			properties: {},
		},
		async execute(_toolCallId, _params, _signal, _onUpdate, _ctx) {
			// Queue /reload as a follow-up command to trigger the reload
			pi.sendUserMessage("/reload", { deliverAs: "followUp" });
			return {
				content: [{ type: "text", text: "Reload queued." }],
			};
		},
	});
}
