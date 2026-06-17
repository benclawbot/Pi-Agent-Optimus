/**
 * Auto-Skill-Suggest Extension
 *
 * Hermes parity: after every agent turn, detect if a reusable workflow
 * was discovered and auto-create a skill for it.
 *
 * Mirrors Hermes `skill_manage`:
 *   - 4 trigger conditions (5+ tool calls, errors + found path, user
 *     correction, non-trivial workflow)
 *   - LLM judges reusability (the agent itself, via injected reflection)
 *   - Auto-creates the skill and notifies the user
 *   - Cross-session dedup against existing skills
 *
 * Detection is structural (cheap, in extension). Judgment is delegated
 * to the agent's LLM via a follow-up reflection prompt.
 *
 * Cooldown: max 1 reflection per N turns (default 3) to avoid spam.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const SKILLS_DIR = join(homedir(), ".pi", "agent", "skills");
const MIN_TOOL_CALLS = 5;
const COOLDOWN_TURNS = 3;
const MAX_EXISTING_LISTED = 30;
const SPAM = [/^\s*\/reload\b/i, /^\s*\/new\b/i, /^\s*\/reset\b/i, /^\s*\/skill:/i];
const CORRECTION_RE = /\b(no|wrong|actually|instead|redo|fix this|not right|nope|try again|that's not|do not|don't|stop|wait)\b/i;

interface ToolCall { name?: string; }
interface Message { role: string; content?: any[]; toolCalls?: ToolCall[]; }

let errorsThisTurn = 0;
let turnsSinceLastSuggest = COOLDOWN_TURNS;
let lastSuggestSignature = "";

function getToolNames(messages: Message[]): string[] {
	const out: string[] = [];
	for (const m of messages) {
		if (m.toolCalls) for (const t of m.toolCalls) if (t?.name) out.push(t.name);
		if (Array.isArray(m.content)) {
			for (const c of m.content) if ((c as any)?.type === "toolCall" && (c as any)?.name) out.push((c as any).name);
		}
	}
	return out;
}

function getFirstUserText(messages: Message[]): string {
	for (const m of messages) {
		if (m.role !== "user") continue;
		const text = Array.isArray(m.content)
			? m.content.filter((c: any) => c?.type === "text").map((c: any) => c.text).join(" ").trim()
			: "";
		if (text && text.length >= 20 && !SPAM.some((p) => p.test(text))) return text;
	}
	return "";
}

function listExistingSkills(): string[] {
	if (!existsSync(SKILLS_DIR)) return [];
	try {
		return readdirSync(SKILLS_DIR, { withFileTypes: true })
			.filter((d) => d.isDirectory())
			.map((d) => d.name)
			.sort();
	} catch {
		return [];
	}
}

function turnSignature(messages: Message[]): string {
	return getFirstUserText(messages).slice(0, 160);
}

export default function autoSkillSuggestExtension(pi: ExtensionAPI) {
	pi.on("turn_start", async () => {
		errorsThisTurn = 0;
		turnsSinceLastSuggest++;
	});

	pi.on("tool_error", async () => {
		errorsThisTurn++;
	});

	pi.on("agent_end", async (event: any, ctx: any) => {
		try {
			const messages: Message[] = event?.messages || [];
			if (!messages.length) return;

			const tools = getToolNames(messages);
			const problem = getFirstUserText(messages);
			if (!problem) return;

			// Hermes trigger 1+4: complex task (5+ calls) or non-trivial workflow
			const isComplex = tools.length >= MIN_TOOL_CALLS;
			// Hermes trigger 2: errors + found working path
			const errorsThenFixed = errorsThisTurn > 0 && tools.length > errorsThisTurn;
			// Hermes trigger 3: user corrected approach
			const userCorrected = CORRECTION_RE.test(problem);

			if (!isComplex && !errorsThenFixed && !userCorrected) return;
			if (turnsSinceLastSuggest < COOLDOWN_TURNS) return;

			const sig = turnSignature(messages);
			if (sig && sig === lastSuggestSignature) return;

			const existing = listExistingSkills();
			const existingLine = existing.length
				? `Existing skills (don't duplicate unless meaningfully different): ${existing.slice(0, MAX_EXISTING_LISTED).join(", ")}${existing.length > MAX_EXISTING_LISTED ? `, ... (+${existing.length - MAX_EXISTING_LISTED} more)` : ""}`
				: "No existing skills yet.";

			lastSuggestSignature = sig;
			turnsSinceLastSuggest = 0;

			// Auto-create (Hermes parity): inject reflection prompt, let LLM judge and act.
			// The agent either uses /skill-creator to draft + write, or reports why not.
			pi.sendUserMessage(
				`[auto-skill-suggest — Hermes parity] Reflection on the turn you just completed.\n\n` +
				`Signals: toolCalls=${tools.length}, errors=${errorsThisTurn}, userCorrection=${userCorrected}.\n\n` +
				`Decide: was this a reusable workflow that future sessions would benefit from? ` +
				`(Examples: non-obvious fix, error→resolution path, user-corrected approach, non-trivial multi-step process, ` +
				`discovered convention, project-specific gotcha.)\n\n` +
				`If YES: load /skill-creator and follow it to draft + save a SKILL.md. Then tell me: skill name + one-line description + the trigger that should activate it.\n` +
				`If NO: reply with one line explaining the heuristic you applied, so this extension can learn.\n\n` +
				`${existingLine}`,
				{ deliverAs: "followUp" }
			);

			if (ctx?.ui?.notify) ctx.ui.notify("Auto-skill: reflect on turn", "info", { duration: 1500 });
		} catch {
			// never break the session
		}
	});
}
