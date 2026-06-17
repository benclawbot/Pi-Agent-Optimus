/**
 * Auto-Skill-Suggest Extension
 *
 * After a complex agent turn (5+ tool calls, mixed read + edit/exec),
 * suggests to the user: "Want me to save this workflow as a skill?"
 *
 * Mirrors Hermes agent's `skill_manage` behavior (autonomous skill creation
 * after complex tasks) but stops one step short of auto-creating: the
 * agent drafts and writes the skill only after the user confirms.
 *
 * Triggers (any one):
 *   - 5+ tool calls in the turn
 *   - Mix of read + edit/exec (not pure browse, not pure chat)
 *   - At least one edit/exec (real work happened)
 *
 * Skips:
 *   - < 5 tool calls (trivial)
 *   - Single tool category (just reads, just writes, just chat)
 *   - /reload / /skill: spam
 *   - Turn that just suggested a skill (avoid self-loop)
 *   - User already declined once this turn (don't pester)
 *
 * Behavior:
 *   Sends a follow-up user message via pi.sendUserMessage with a short
 *   summary. The agent then drafts the skill via skill-creator if the
 *   user says yes.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

const MIN_TOOL_CALLS = 5;
const SPAM = [/^\s*\/reload\s*$/i, /^\s*\/skill:/i, /^\s*\/new\s*$/i, /^\s*\/reset\s*$/i];

interface ToolCall {
	name: string;
}

interface Message {
	role: string;
	content?: any[];
	toolCalls?: ToolCall[];
}

function getToolNames(messages: Message[]): string[] {
	const out: string[] = [];
	for (const m of messages) {
		if (m.toolCalls) for (const t of m.toolCalls) if (t?.name) out.push(t.name);
		if (m.content) {
			for (const c of m.content) {
				if (c?.type === "toolCall" && c?.name) out.push(c.name);
			}
		}
	}
	return out;
}

function getFirstUserText(messages: Message[]): string {
	for (const m of messages) {
		if (m.role !== "user") continue;
		const text = m.content
			?.filter((c: any) => c.type === "text")
			?.map((c: any) => c.text)
			?.join(" ")
			?.trim();
		if (text && text.length >= 20 && !SPAM.some((p) => p.test(text))) {
			return text;
		}
	}
	return "";
}

function categorize(tools: string[]): Set<string> {
	const cats = new Set<string>();
	const lower = tools.map((t) => t.toLowerCase());
	if (lower.some((t) => /^(read|get)$/.test(t))) cats.add("read");
	if (lower.some((t) => /^(write|edit|create)$/.test(t) || t.includes("edit"))) cats.add("edit");
	if (lower.some((t) => /^(bash|exec|execute_command|execute)/.test(t))) cats.add("exec");
	if (lower.some((t) => /^(grep|search|find|repo_map)$/.test(t))) cats.add("search");
	return cats;
}

let lastSuggestKey = "";

function turnKey(messages: Message[]): string {
	const firstUser = getFirstUserText(messages);
	return firstUser.slice(0, 120);
}

export default function autoSkillSuggestExtension(pi: ExtensionAPI) {
	pi.on("agent_end", async (event: any, ctx: any) => {
		try {
			const messages: Message[] = event?.messages || [];
			if (!messages.length) return;

			const tools = getToolNames(messages);
			if (tools.length < MIN_TOOL_CALLS) return;

			const cats = categorize(tools);
			if (cats.size < 2) return; // single-mode turn
			if (!cats.has("edit") && !cats.has("exec")) return; // no real work

			const problem = getFirstUserText(messages);
			if (!problem) return;

			const key = turnKey(messages);
			if (key === lastSuggestKey) return; // dedup across turns with same prompt

			lastSuggestKey = key;

			const summary = problem.slice(0, 100);
			const toolSig = [...new Set(tools.map((t) => t.toLowerCase()))].slice(0, 6).join(", ");

			if (ctx?.ui && typeof ctx.ui.notify === "function") {
				ctx.ui.notify("Skill-suggest: complex task detected", "info", { duration: 1500 });
			}

			pi.sendUserMessage(
				`[auto-skill-suggest] I just finished a multi-step task: "${summary}" ` +
				`(used ${tools.length} calls: ${toolSig}). ` +
				`If this workflow is likely to come up again, I can save it as a skill. ` +
				`Want me to draft one with /skill-creator? (yes / no / not now)`,
				{ deliverAs: "followUp" }
			);
		} catch {
			// Never break the session on extension error
		}
	});
}

