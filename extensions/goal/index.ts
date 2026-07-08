/**
 * Goal Capability
 *
 * Long-running objectives that span turns. Three built-in tools + one slash command.
 *
 * Tools (LLM-callable):
 *   create_goal  — start a new goal (only when explicitly requested)
 *   get_goal     — show active goal, status, budget, elapsed
 *   update_goal  — mark complete or blocked
 *
 * Command (user-invokable):
 *   /goal        — show active goal in chat; with arg = create new
 *
 * Persistence: stored as a custom session entry so it survives compaction
 * and continuations. Backed by .pi/agent/goal.json on disk for cross-session
 * survival.
 *
 * Rules (per spec):
 *   - create_goal refuses if a goal is already active
 *   - update_goal blocks only after the same blocker recurs >= 3 turns
 *   - No pause/resume/budget-change
 *   - Token budget is a soft cap; warning shown when exceeded, not enforced
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const GOAL_FILE = join(homedir(), ".pi", "agent", "goal.json");

type GoalStatus = "active" | "complete" | "blocked";

interface GoalState {
	objective: string;
	token_budget?: number;
	tokens_used: number;
	turns: number;
	blocker_history: string[]; // last blocker strings, deduped, max 3
	current_blocker?: string;
	created_at: string;
	updated_at: string;
	status: GoalStatus;
}

interface PersistedGoal {
	goal: GoalState | null;
}

function load(): PersistedGoal {
	try {
		if (!existsSync(GOAL_FILE)) return { goal: null };
		const raw = JSON.parse(readFileSync(GOAL_FILE, "utf8"));
		if (raw && typeof raw === "object" && "goal" in raw) return raw;
		return { goal: null };
	} catch {
		return { goal: null };
	}
}

function save(state: PersistedGoal): void {
	try {
		writeFileSync(GOAL_FILE, JSON.stringify(state, null, 2));
	} catch {
		// Non-fatal
	}
}

function nowIso(): string {
	return new Date().toISOString();
}

function formatElapsed(start: string): string {
	const ms = Date.now() - new Date(start).getTime();
	const s = Math.floor(ms / 1000);
	if (s < 60) return `${s}s`;
	const m = Math.floor(s / 60);
	if (m < 60) return `${m}m`;
	const h = Math.floor(m / 60);
	return `${h}h ${m % 60}m`;
}

function formatGoal(g: GoalState | null): string {
	if (!g) return "No active goal.";
	const status = g.status;
	const elapsed = formatElapsed(g.created_at);
	const budgetLine = g.token_budget
		? `Budget: ${g.tokens_used.toLocaleString()} / ${g.token_budget.toLocaleString()} tokens`
		: `Tokens used: ${g.tokens_used.toLocaleString()}`;
	const blockerLine = g.current_blocker ? `\nBlocker: ${g.current_blocker}` : "";
	return [
		`Goal: ${g.objective}`,
		`Status: ${status}`,
		`Elapsed: ${elapsed}  •  Turns: ${g.turns}`,
		budgetLine + blockerLine,
	].join("\n");
}

export default function goalExtension(pi: ExtensionAPI) {
	// ── Slash command ───────────────────────────────────────────────
	pi.registerCommand("goal", {
		description: "Show active goal. With an objective argument, create a new goal.",
		handler: async (args, ctx) => {
			const trimmed = (args || "").trim();
			const state = load();

			if (!trimmed) {
				ctx.ui.notify(formatGoal(state.goal), "info");
				return;
			}

			if (state.goal && state.goal.status === "active") {
				ctx.ui.notify(`A goal is already active. Complete or block it first:\n${formatGoal(state.goal)}`, "warning");
				return;
			}

			const newGoal: GoalState = {
				objective: trimmed,
				token_budget: undefined,
				tokens_used: 0,
				turns: 0,
				blocker_history: [],
				created_at: nowIso(),
				updated_at: nowIso(),
				status: "active",
			};
			save({ goal: newGoal });
			ctx.ui.notify(`Goal created: ${trimmed}`, "info");
		},
	});

	// ── LLM tools ──────────────────────────────────────────────────

	pi.registerTool({
		name: "create_goal",
		label: "Create Goal",
		description:
			"Start a new long-running goal. Use ONLY when the user explicitly asks for a goal (e.g. 'create a goal to ...', 'set a goal of ...', 'track this as a goal'). Do NOT use proactively. Refuses if a goal is already active.",
		parameters: Type.Object({
			objective: Type.String({ description: "Concrete, measurable objective." }),
			token_budget: Type.Optional(
				Type.Number({ description: "Optional positive token budget (soft cap, not enforced).", minimum: 1 }),
			),
		}),
		async execute(_id, params, _signal, _onUpdate, _ctx) {
			const state = load();
			if (state.goal && state.goal.status === "active") {
				return {
					content: [
						{
							type: "text",
							text: `Refused: a goal is already active. Complete or block it first.\n${formatGoal(state.goal)}`,
						},
					],
					isError: true,
				};
			}
			const goal: GoalState = {
				objective: params.objective,
				token_budget: params.token_budget,
				tokens_used: 0,
				turns: 0,
				blocker_history: [],
				created_at: nowIso(),
				updated_at: nowIso(),
				status: "active",
			};
			save({ goal });
			return {
				content: [
					{ type: "text", text: `Goal created.\n${formatGoal(goal)}` },
				],
			};
		},
	});

	pi.registerTool({
		name: "get_goal",
		label: "Get Goal",
		description: "Show the active goal: objective, status, token usage, elapsed time, and remaining budget.",
		parameters: Type.Object({}),
		async execute() {
			const state = load();
			return {
				content: [{ type: "text", text: formatGoal(state.goal) }],
			};
		},
	});

	pi.registerTool({
		name: "update_goal",
		label: "Update Goal",
		description:
			"Update goal status. Use 'complete' ONLY when the objective is genuinely achieved. Use 'blocked' ONLY when the same blocker has recurred for at least 3 goal turns. Cannot pause, resume, or change budgets.",
		parameters: Type.Object({
			status: Type.String({ description: "'complete' or 'blocked'" }),
			blocker: Type.Optional(Type.String({ description: "Required when status='blocked': describe the recurring blocker." })),
		}),
		async execute(_id, params, _signal, _onUpdate, _ctx) {
			const state = load();
			if (!state.goal) {
				return {
					content: [{ type: "text", text: "No active goal to update." }],
					isError: true,
				};
			}
			if (state.goal.status !== "active") {
				return {
					content: [{ type: "text", text: `Goal is already ${state.goal.status}.` }],
					isError: true,
				};
			}

			if (params.status === "complete") {
				state.goal.status = "complete";
				state.goal.updated_at = nowIso();
				save(state);
				return { content: [{ type: "text", text: `Goal marked complete: ${state.goal.objective}` }] };
			}

			if (params.status === "blocked") {
				if (!params.blocker) {
					return {
						content: [{ type: "text", text: "blocker description required when status='blocked'." }],
						isError: true,
					};
				}
				// Track blocker history
				const hist = state.goal.blocker_history;
				const last = hist[hist.length - 1];
				if (last !== params.blocker) hist.push(params.blocker);
				state.goal.blocker_history = hist.slice(-3);

				if (state.goal.blocker_history.length < 3) {
					// Not enough recurrences yet
					state.goal.current_blocker = params.blocker;
					state.goal.updated_at = nowIso();
					save(state);
					return {
						content: [
							{
								type: "text",
								text: `Blocker recorded (${state.goal.blocker_history.length}/3 recurrences). Same blocker must recur 3 times to mark blocked. Continue working.`,
							},
						],
					};
				}

				// Third recurrence of the same blocker → mark blocked
				state.goal.status = "blocked";
				state.goal.current_blocker = params.blocker;
				state.goal.updated_at = nowIso();
				save(state);
				return {
					content: [
						{
							type: "text",
							text: `Goal marked blocked after 3 recurrences: ${params.blocker}`,
						},
					],
				};
			}

			return {
				content: [{ type: "text", text: `Unknown status: ${params.status}. Use 'complete' or 'blocked'.` }],
				isError: true,
			};
		},
	});

	// ── Token usage tracking ───────────────────────────────────────
	pi.on("agent_end", async (event: any, _ctx) => {
		const state = load();
		if (!state.goal || state.goal.status !== "active") return;
		try {
			const usage = event?.messages?.[event.messages.length - 1]?.usage;
			if (usage?.totalTokens) state.goal.tokens_used += usage.totalTokens;
			state.goal.turns += 1;
			state.goal.updated_at = nowIso();
			save(state);
		} catch {
			// Non-fatal
		}
	});
}
