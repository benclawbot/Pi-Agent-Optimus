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
			// Trigger the actual reload via the runtime API.
			// Do NOT use sendUserMessage("/reload", { deliverAs: "followUp" }) — that
			// re-injects /reload as a new user turn, which the model then answers by
			// calling pi_reload again, creating an infinite loop.
			await pi.reload();
			return { content: [{ type: "text", text: "Reloaded." }] };
		},
	});
}
