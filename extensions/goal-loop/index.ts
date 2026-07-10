/**
 * goal-loop — Ralph loop driver for the existing `~/.pi/agent/extensions/goal` extension.
 *
 * The existing extension gives the LLM `create_goal` / `get_goal` / `update_goal`
 * tools and tracks goal state in `~/.pi/agent/goal.json`. What it does NOT do is
 * drive the autonomous loop: after every turn, judge the latest response, and if
 * the goal isn't done, send the agent back in for another turn.
 *
 * This extension is the missing piece. On `turn_end`:
 *   1. Load the active goal from `~/.pi/agent/goal.json` (set by the existing
 *      extension's `create_goal` tool or `/goal <text>` slash).
 *   2. Skip if status != active, or if a real user message is queued (preempt).
 *   3. Call the auxiliary judge model (OpenAI-compatible).
 *   4. If judge says done / blocked -> mark complete / blocked via the
 *      same goal.json the existing extension reads.
 *   5. If judge says continue AND turns < budget -> sendUserMessage(continuation
 *      prompt) so the next turn runs in the same session.
 *   6. Auto-pause on budget exhaustion or N consecutive judge parse failures.
 *
 * Mirror of Hermes `hermes_cli/cli.py:_maybe_continue_goal_after_turn` +
 * `hermes_cli/goals.py:GoalManager.evaluate_after_turn`.
 */

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

import {
	DEFAULT_JUDGE_MAX_TOKENS,
	DEFAULT_JUDGE_TIMEOUT_MS,
	JudgeConfig,
	judgeGoal,
} from "./judge.js";

interface PersistedGoal {
	goal: {
		objective: string;
		status: "active" | "complete" | "blocked";
		token_budget?: number;
		tokens_used: number;
		turns: number;
		created_at: string;
		updated_at: string;
	} | null;
}

const GOAL_FILE = join(homedir(), ".pi", "agent", "goal.json");
const DEFAULT_MAX_TURNS = 20;
const DEFAULT_MAX_PARSE_FAILURES = 3;

function loadGoalFile(): PersistedGoal {
	try {
		if (!existsSync(GOAL_FILE)) return { goal: null };
		const raw = JSON.parse(readFileSync(GOAL_FILE, "utf8"));
		if (raw && typeof raw === "object" && "goal" in raw) return raw as PersistedGoal;
		return { goal: null };
	} catch {
		return { goal: null };
	}
}

function writeGoalFile(persisted: PersistedGoal): void {
	try {
		writeFileSync(GOAL_FILE, JSON.stringify(persisted, null, 2));
	} catch (err) {
		console.warn(`[goal-loop] write failed: ${(err as Error).message}`);
	}
}

function updateActiveGoal(mutator: (g: NonNullable<PersistedGoal["goal"]>) => void): void {
	const persisted = loadGoalFile();
	if (!persisted.goal || persisted.goal.status !== "active") return;
	mutator(persisted.goal);
	persisted.goal.updated_at = new Date().toISOString();
	writeGoalFile(persisted);
}

function resolveJudgeConfig(): JudgeConfig | null {
	const url = process.env.GOAL_LOOP_JUDGE_URL || "";
	const model = process.env.GOAL_LOOP_JUDGE_MODEL || "";
	const apiKey = process.env.GOAL_LOOP_JUDGE_KEY || process.env.OPENAI_API_KEY || "";
	if (!url || !model || !apiKey) return null;
	const envTimeout = Number(process.env.GOAL_LOOP_JUDGE_TIMEOUT_MS);
	const envMax = Number(process.env.GOAL_LOOP_JUDGE_MAX_TOKENS);
	return {
		url,
		model,
		apiKey,
		timeoutMs: Number.isFinite(envTimeout) && envTimeout > 0 ? envTimeout : DEFAULT_JUDGE_TIMEOUT_MS,
		maxTokens: Number.isFinite(envMax) && envMax > 0 ? envMax : DEFAULT_JUDGE_MAX_TOKENS,
	};
}

function resolveMaxTurns(): number {
	const env = Number(process.env.GOAL_LOOP_MAX_TURNS);
	if (Number.isFinite(env) && env > 0) return Math.floor(env);
	return DEFAULT_MAX_TURNS;
}


// ponytail: surface last tool call when assistant produced no prose text
function extractLastToolSummary(branch) {
	for (let i = branch.length - 1; i >= 0; i--) {
		const entry = branch[i];
		if (entry.type !== "message") continue;
		const msg = entry.message;
		if (!msg || msg.role !== "assistant") continue;
		const content = msg.content;
		if (!Array.isArray(content)) continue;
		const calls = [];
		for (const block of content) {
			if (!block || typeof block !== "object") continue;
			const b = block;
			if (b.type === "toolCall" && b.name) calls.push(b.name + "(" + JSON.stringify(b.input || {}).slice(0, 200) + ")");
		}
		if (calls.length) return "agent last action: " + calls.slice(-3).join("; ");
	}
	return undefined;
}
function extractAssistantText(message: unknown): string {
	if (!message || typeof message !== "object") return "";
	const m = message as { role?: string; content?: unknown };
	if (m.role !== "assistant") return "";
	const content = m.content;
	if (typeof content === "string") return content;
	if (Array.isArray(content)) {
		const parts: string[] = [];
		for (const part of content) {
			if (typeof part === "string") {
				parts.push(part);
			} else if (part && typeof part === "object") {
				const p = part as { type?: string; text?: string };
				if ((p.type === "text" || p.type === "output_text") && typeof p.text === "string") {
					parts.push(p.text);
				}
			}
		}
		return parts.join("\n");
	}
	return "";
}

const CONTINUATION_PROMPT = (goal: string) =>
	[
		"[Continuing toward your standing goal]",
		`Goal: ${goal}`,
		"",
		"Continue working toward this goal. Take the next concrete step. ",
		"If you believe the goal is complete, call `update_goal` with status=\"complete\". ",
		"If you are blocked and need input from the user, say so clearly and stop.",
	].join("\n");

// In-memory parse-failure counter, keyed by goal.created_at so a new goal
// resets it. Not persisted — judge health is per-process, not per-session.
let parseFailures = 0;
let lastGoalCreatedAt = "";

export default function (pi: ExtensionAPI) {
	const cfg = resolveJudgeConfig();
	if (!cfg) {
		// Soft-fail. Extension loads, but the loop no-ops. The user gets a
		// notify on the first turn so they know to configure the judge.
		console.warn(
			"[goal-loop] judge not configured. Set GOAL_LOOP_JUDGE_URL, _MODEL, _KEY (or OPENAI_API_KEY).",
		);
	}

	pi.on("turn_end", async (event, ctx) => {
		const persisted = loadGoalFile();
		const goal = persisted.goal;
		if (!goal || goal.status !== "active") return;

		// Reset parse-failure counter when a new goal is loaded.
		if (goal.created_at !== lastGoalCreatedAt) {
			parseFailures = 0;
			lastGoalCreatedAt = goal.created_at;
		}

		// Preempt if a real user message is already pending.
		try {
			const hasPending = (ctx as unknown as { hasPendingMessages?: () => boolean }).hasPendingMessages?.();
			if (hasPending) return;
		} catch {
			// ignore
		}

		const branchForEvent = (event as any).messages ?? (event as any).branch ?? [];
		const lastResponse = extractAssistantText(event.message);
		if (!lastResponse.trim()) return; // empty-response skip (transient API errors)

		const maxTurns = resolveMaxTurns();
		const turnsUsed = (goal.turns ?? 0) + 1;
		const overBudget = turnsUsed >= maxTurns;

		if (!cfg) {
			// Once per goal — remind the user the loop can't run without a judge.
			if (turnsUsed === 1) {
				ctx.ui.notify(
					"goal-loop: judge not configured — automatic continuation disabled. " +
						"Set GOAL_LOOP_JUDGE_URL / _MODEL / _KEY in your env.",
					"warning",
				);
			}
			return;
		}

		const result = await judgeGoal({ goal: goal.objective, lastResponse }, cfg);

		if (result.parse_failed) {
			parseFailures += 1;
		} else {
			parseFailures = 0;
		}

		if (parseFailures >= DEFAULT_MAX_PARSE_FAILURES) {
			updateActiveGoal((g) => {
				g.status = "blocked";
				g.current_blocker = `judge model returned unparseable output ${parseFailures} turns in a row`;
			});
			ctx.ui.notify(
				`⏸ Goal blocked — judge model isn't returning JSON. Configure a stricter model ` +
					`via GOAL_LOOP_JUDGE_MODEL, then /goal ... to restart.`,
				"warning",
			);
			return;
		}

		if (result.verdict === "done") {
			updateActiveGoal((g) => {
				g.status = "complete";
			});
			ctx.ui.notify(`✓ Goal achieved: ${result.reason}`, "info");
			return;
		}

		if (overBudget) {
			updateActiveGoal((g) => {
				g.status = "blocked";
				g.current_blocker = `goal-loop: turn budget exhausted (${turnsUsed}/${maxTurns})`;
			});
			ctx.ui.notify(
				`⏸ Goal blocked — ${turnsUsed}/${maxTurns} turns used. Mark complete or start a new goal.`,
				"warning",
			);
			return;
		}

		// Continue: send the continuation prompt as the next user message.
		try {
			await pi.sendUserMessage(CONTINUATION_PROMPT(goal.objective), { deliverAs: "followUp" });
			ctx.ui.notify(`↻ Continuing toward goal (${turnsUsed}/${maxTurns}): ${result.reason}`, "info");
		} catch (err) {
			console.warn(`[goal-loop] sendUserMessage failed: ${(err as Error).message}`);
		}
	});
}
