/**
 * BTW Extension
 *
 * Provides a /btw command for side-band input — clarifications, steering,
 * or notes that should be considered without interrupting the flow.
 *
 * Usage:
 *   /btw <message>  — stores the message and adds it to context
 *
 * The message is injected as a "steer" message so the agent considers it
 * without a full turn interruption.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { existsSync, readFileSync, appendFileSync, writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import os from "node:os";

function getBtwDir(): string {
	return path.join(os.homedir(), ".pi", "btw");
}

function ensureBtwDir(): void {
	const dir = getBtwDir();
	if (!existsSync(dir)) {
		mkdirSync(dir, { recursive: true });
	}
}

function getBtwFile(): string {
	return path.join(getBtwDir(), "messages.md");
}

function getReasoningStateFile(): string {
	return path.join(getBtwDir(), "reasoning-state.json");
}

interface ReasoningState {
	enabled: boolean;
}

function loadReasoningState(): ReasoningState {
	const file = getReasoningStateFile();
	if (existsSync(file)) {
		try {
			return JSON.parse(readFileSync(file, "utf8"));
		} catch {
			// ignore
		}
	}
	return { enabled: false };
}


function saveReasoningState(state: ReasoningState): void {
	ensureBtwDir();
	writeFileSync(getReasoningStateFile(), JSON.stringify(state), "utf8");
}

export default function btwExtension(pi: ExtensionAPI) {
	pi.registerCommand("btw", {
		description: "Add a side-band note or clarification (doesn't interrupt flow)",
		usage: "/btw <your note or clarification>",
		handler: async (args, ctx) => {
			const message = args.trim();

			if (!message) {
				if (ctx.hasUI) {
					ctx.ui.notify("Usage: /btw <your note or clarification>", "error");
				}
				return;
			}

			ensureBtwDir();
			const btwFile = getBtwFile();
			const timestamp = new Date().toLocaleString();

			// Append to the btw file for persistence
			const entry = `**${timestamp}:** ${message}\n`;
			appendFileSync(btwFile, entry, "utf8");

			// Deliver as steer message so agent considers it without interrupting
			pi.sendUserMessage(
				`[BTW] ${message}`,
				{ deliverAs: "steer" }
			);

			if (ctx.hasUI) {
				ctx.ui.notify("Added to context", "info", { duration: 1500 });
			}
		}
	});

	// Also expose a tool to read all btw messages
	pi.registerTool({
		name: "btw_read",
		label: "Read BTW Messages",
		description: "Read all stored /btw messages for the current session",
		parameters: {
			type: "object",
			properties: {}
		},
		async execute(_toolCallId, _params, _signal, _onUpdate, _ctx) {
			const btwFile = getBtwFile();

			if (!existsSync(btwFile)) {
				return {
					content: [{ type: "text", text: "No /btw messages recorded yet." }],
				};
			}

			const content = readFileSync(btwFile, "utf8");
			return {
				content: [{ type: "text", text: `BTW Messages:\n${content}` }],
			};
		}
	});

	// Tool to clear btw messages
	pi.registerTool({
		name: "btw_clear",
		label: "Clear BTW Messages",
		description: "Clear all stored /btw messages",
		parameters: {
			type: "object",
			properties: {}
		},
		async execute(_toolCallId, _params, _signal, _onUpdate, ctx) {
			const btwFile = getBtwFile();

			if (existsSync(btwFile)) {
				writeFileSync(btwFile, "", "utf8");
			}

			if (ctx.hasUI) {
				ctx.ui.notify("BTW messages cleared", "info", { duration: 1500 });
			}

			return {
				content: [{ type: "text", text: "BTW messages cleared." }],
			};
		}
	});

	// Apply saved reasoning state on session start
	pi.events.on("session_start", () => {
		const state = loadReasoningState();
		if (state.enabled) {
			pi.setThinkingLevel("medium");
		} else {
			pi.setThinkingLevel("off");
		}
	});

	// /reasoning command — toggle extended reasoning on/off
	pi.registerCommand("reasoning", {
		description: "Toggle extended reasoning (thinking) on/off",
		usage: "/reasoning [on|off|toggle] — no arg shows current state",
		handler: async (args, ctx) => {
			const arg = args.trim().toLowerCase();
			const state = loadReasoningState();

			const currentEnabled = state.enabled;

			let newEnabled: boolean;

			if (arg === "" || arg === "status") {
				// Show current state
				const statusMsg = currentEnabled ? "Reasoning: ON (extended thinking enabled)" : "Reasoning: OFF (no extended thinking)";
				if (ctx.hasUI) {
					ctx.ui.notify(statusMsg, "info", { duration: 2000 });
				} else {
					console.log(statusMsg);
				}
				return;
			}

			if (arg === "toggle") {
				newEnabled = !currentEnabled;
			} else if (arg === "on") {
				newEnabled = true;
			} else if (arg === "off") {
				newEnabled = false;
			} else {
				if (ctx.hasUI) {
					ctx.ui.notify("Usage: /reasoning [on|off|toggle]", "error");
				}
				return;
			}

			state.enabled = newEnabled;
			saveReasoningState(state);

			if (newEnabled) {
				pi.setThinkingLevel("medium");
				if (ctx.hasUI) {
					ctx.ui.notify("Reasoning ON — extended thinking enabled", "info", { duration: 2000 });
				}
			} else {
				pi.setThinkingLevel("off");
				if (ctx.hasUI) {
					ctx.ui.notify("Reasoning OFF — no extended thinking", "info", { duration: 2000 });
				}
			}
		}
	});
}
