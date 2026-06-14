/**
 * long_task Tools
 *
 * Filesystem-as-memory ritual for long-horizon work. Implements Anthropic's
 * "context discovery over compaction" pattern: when the agent resumes in a
 * fresh context window, it calls `pwd`, reads a progress file, and continues.
 *
 * Two tools:
 *   - long_task_start: create .pi-progress.md with goal, plan, state, log
 *   - long_task_resume: read .pi-progress.md and emit a status summary
 *   - long_task_checkpoint: append to the log, update state
 *   - long_task_finish: mark done, archive the progress file
 *
 * The progress file is in cwd, not the agent's session dir — it travels
 * with the work.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { readFileSync, writeFileSync, existsSync, renameSync, mkdirSync, readdirSync, statSync } from "node:fs";
import { join, isAbsolute } from "node:path";

const PROGRESS_FILENAME = ".pi-progress.md";
const PROGRESS_DIR = ".pi-progress";

function progressPath(cwd: string): string {
	return join(cwd, PROGRESS_FILENAME);
}

function archivePath(cwd: string, ts: number): string {
	const dir = join(cwd, PROGRESS_DIR);
	if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
	return join(dir, `progress-${ts}.md`);
}

function nowIso(): string {
	return new Date().toISOString();
}

function nowStamp(): number {
	return Date.now();
}

interface ProgressState {
	goal: string;
	plan: string[];
	state: string;
	log: string[];
	startedAt: string;
	lastUpdated: string;
	blocked?: string;
}

function parseProgress(text: string): ProgressState | null {
	const m = text.match(/^<!--\s*PI-PROGRESS\s*([\s\S]*?)\s*-->/);
	if (!m) return null;
	try {
		const obj = JSON.parse(m[1]) as ProgressState;
		if (!obj.goal || !Array.isArray(obj.plan) || !Array.isArray(obj.log)) return null;
		return obj;
	} catch {
		return null;
	}
}

function serializeProgress(state: ProgressState): string {
	const header = `<!-- PI-PROGRESS ${JSON.stringify(state)} -->`;
	return `${header}\n# ${state.goal}\n\n**Started:** ${state.startedAt}  \n**Last updated:** ${state.lastUpdated}\n\n## Plan\n\n${state.plan.map((p, i) => `${i + 1}. ${p}`).join("\n")}\n\n## Current state\n\n${state.state}\n\n## Log\n\n${state.log.map((l) => `- ${l}`).join("\n")}\n${state.blocked ? `\n## Blocked\n\n${state.blocked}\n` : ""}\n`;
}

function findExistingProgress(cwd: string): string | null {
	// Check cwd, then walk up
	let dir = cwd;
	for (let i = 0; i < 5; i++) {
		const p = join(dir, PROGRESS_FILENAME);
		if (existsSync(p)) return p;
		const parent = join(dir, "..");
		if (parent === dir) break;
		dir = parent;
	}
	return null;
}

export default function longTaskExtension(pi: ExtensionAPI) {
	pi.registerTool({
		name: "long_task_start",
		label: "Start Long Task",
		description:
			"Start a long-horizon task by writing a progress file to cwd. Use this when the task may span compaction, /clear, or session restart. The progress file is the canonical recovery point — the agent in a future fresh context window reads it via long_task_resume to continue.",
		promptSnippet: "long_task_start(goal, plan[]) — create a recoverable progress file",
		promptGuidelines: [
			"Call long_task_start for any task expected to take more than ~10 turns or span a compaction boundary.",
			"Pass the goal and a concrete numbered plan. Vague plans produce vague resumes.",
			"After starting, call long_task_checkpoint at meaningful milestones.",
		],
		parameters: Type.Object({
			goal: Type.String({ description: "One-sentence goal. Concrete and falsifiable." }),
			plan: Type.Array(Type.String(), {
				description: "Numbered plan steps. Use [] if you'll fill in later.",
			}),
			state: Type.Optional(
				Type.String({
					description: "Current state description. Defaults to 'just started'.",
					default: "just started",
				}),
			),
			cwd: Type.Optional(Type.String({ description: "Working directory. Defaults to process.cwd()." })),
		}),
		async execute(_id, params) {
			const cwd = params.cwd || process.cwd();
			if (!isAbsolute(cwd)) return { content: [{ type: "text", text: `cwd must be absolute: ${cwd}` }], details: { error: true } };
			const path = progressPath(cwd);
			if (existsSync(path)) {
				return {
					content: [{ type: "text", text: `Progress file already exists at ${path}. Use long_task_resume to read it, or delete it first if you're starting over.` }],
					details: { exists: true, path },
				};
			}
			const now = nowIso();
			const state: ProgressState = {
				goal: params.goal,
				plan: params.plan,
				state: params.state || "just started",
				log: [`started at ${now}`],
				startedAt: now,
				lastUpdated: now,
			};
			writeFileSync(path, serializeProgress(state), "utf8");
			return {
				content: [
					{
						type: "text",
						text: `Long task started. Progress file: ${path}\n\nGoal: ${state.goal}\nPlan: ${state.plan.length} steps\n\nNext: call long_task_checkpoint as you make progress.`,
					},
				],
				details: { path, goal: state.goal, planLen: state.plan.length },
			};
		},
	});

	pi.registerTool({
		name: "long_task_resume",
		label: "Resume Long Task",
		description:
			"Read the progress file (in cwd or up to 5 parents) and emit a structured resume prompt. Use this in a fresh context window to pick up where a previous session left off.",
		promptSnippet: "long_task_resume(cwd?) — recover state from .pi-progress.md",
		parameters: Type.Object({
			cwd: Type.Optional(Type.String({ description: "Working directory. Defaults to process.cwd()." })),
		}),
		async execute(_id, params) {
			const cwd = params.cwd || process.cwd();
			const found = findExistingProgress(cwd);
			if (!found) {
				return {
					content: [{ type: "text", text: `No progress file found in ${cwd} or up to 5 parents.` }],
					details: { found: false },
				};
			}
			const text = readFileSync(found, "utf8");
			const state = parseProgress(text);
			if (!state) {
				return {
					content: [{ type: "text", text: `Progress file exists at ${found} but failed to parse. Raw content:\n\n${text}` }],
					details: { found: true, parsed: false, path: found },
				};
			}
			const elapsed = Date.now() - new Date(state.startedAt).getTime();
			const hours = Math.floor(elapsed / 3_600_000);
			const mins = Math.floor((elapsed % 3_600_000) / 60_000);
			const summary = [
				`# Resume: ${state.goal}`,
				``,
				`**Started:** ${state.startedAt} (${hours}h ${mins}m ago)`,
				`**Last updated:** ${state.lastUpdated}`,
				``,
				`## Plan (${state.plan.length} steps)`,
				...state.plan.map((p, i) => `${i + 1}. ${p}`),
				``,
				`## Current state`,
				state.state,
				``,
				`## Recent log (last 10)`,
				...state.log.slice(-10).map((l) => `- ${l}`),
				``,
				`## Next action`,
				state.blocked
					? `BLOCKED: ${state.blocked}\nResolve the blocker before continuing.`
					: `Pick the first incomplete plan step and continue. Update state via long_task_checkpoint after each meaningful change.`,
			].join("\n");
			return {
				content: [{ type: "text", text: summary }],
				details: {
					found: true,
					parsed: true,
					path: found,
					planLen: state.plan.length,
					logLen: state.log.length,
					blocked: !!state.blocked,
				},
			};
		},
	});

	pi.registerTool({
		name: "long_task_checkpoint",
		label: "Checkpoint Long Task",
		description:
			"Update the progress file: log a milestone, change the state description, mark a plan step done, or record a blocker. Use this between major steps so a future resume starts with current context.",
		parameters: Type.Object({
			state: Type.Optional(Type.String({ description: "New current-state description (replaces previous)." })),
			log: Type.Optional(Type.String({ description: "Append a single log line." })),
			complete_step: Type.Optional(Type.Number({ description: "0-indexed plan step to mark complete (strikethrough)." })),
			blocked: Type.Optional(Type.String({ description: "Mark task as blocked with this reason (or pass empty string to unblock)." })),
			cwd: Type.Optional(Type.String({ description: "Working directory. Defaults to process.cwd()." })),
		}),
		async execute(_id, params) {
			const cwd = params.cwd || process.cwd();
			const found = findExistingProgress(cwd);
			if (!found) {
				return { content: [{ type: "text", text: `No progress file found in ${cwd} or parents. Call long_task_start first.` }], details: { error: true } };
			}
			const text = readFileSync(found, "utf8");
			const state = parseProgress(text);
			if (!state) {
				return { content: [{ type: "text", text: `Progress file at ${found} failed to parse. Delete it manually and re-start.` }], details: { error: true } };
			}
			if (params.state !== undefined) state.state = params.state;
			if (params.log) state.log.push(`${nowIso()}: ${params.log}`);
			if (typeof params.complete_step === "number") {
				const i = params.complete_step;
				if (i >= 0 && i < state.plan.length) {
					state.plan[i] = `~~${state.plan[i]}~~ ✓`;
				}
			}
			if (params.blocked !== undefined) {
				state.blocked = params.blocked || undefined;
				if (state.blocked) state.log.push(`${nowIso()}: BLOCKED — ${state.blocked}`);
			}
			state.lastUpdated = nowIso();
			writeFileSync(found, serializeProgress(state), "utf8");
			return {
				content: [
					{
						type: "text",
						text: `Checkpoint saved to ${found}\nState: ${state.state}\nLog entries: ${state.log.length}${state.blocked ? `\nBLOCKED: ${state.blocked}` : ""}`,
					},
				],
				details: { path: found, state: state.state, logLen: state.log.length, blocked: !!state.blocked },
			};
		},
	});

	pi.registerTool({
		name: "long_task_finish",
		label: "Finish Long Task",
		description: "Mark the task complete and archive the progress file to .pi-progress/progress-<ts>.md.",
		parameters: Type.Object({
			summary: Type.String({ description: "One-paragraph summary of what was done." }),
			cwd: Type.Optional(Type.String({ description: "Working directory. Defaults to process.cwd()." })),
		}),
		async execute(_id, params) {
			const cwd = params.cwd || process.cwd();
			const found = findExistingProgress(cwd);
			if (!found) {
				return { content: [{ type: "text", text: `No progress file found in ${cwd} or parents.` }], details: { error: true } };
			}
			const text = readFileSync(found, "utf8");
			const state = parseProgress(text);
			if (!state) {
				return { content: [{ type: "text", text: `Progress file at ${found} failed to parse.` }], details: { error: true } };
			}
			state.log.push(`${nowIso()}: FINISHED — ${params.summary}`);
			state.state = `done: ${params.summary}`;
			state.lastUpdated = nowIso();
			const archive = archivePath(cwd, nowStamp());
			writeFileSync(archive, serializeProgress(state), "utf8");
			try {
				renameSync(found, `${found}.done`);
			} catch {
				// ignore — archive is the canonical record
			}
			return {
				content: [{ type: "text", text: `Task finished. Archived to ${archive}` }],
				details: { archive, summary: params.summary },
			};
		},
	});
}
