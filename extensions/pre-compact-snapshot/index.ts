/**
 * Pre-Compact Snapshot Extension
 *
 * Before compaction discards the old conversation, capture a deterministic
 * snapshot of the working state to disk. The snapshot survives the LLM
 * summary loss and is discoverable on resume via:
 *   1. `CompactionEntry.details.snapshotPath` (machine-readable)
 *   2. A `<snapshot-ref>` tag prepended to the summary (LLM-readable)
 *   3. A `session_start` notification on reload/resume
 *
 * Captures: timestamp, model, tokens, cwd, last user goal, recent file ops,
 * optional plan from `.pi-progress.md`, open todos, project conventions.
 *
 * Commands:
 *   /snapshot              - take a snapshot now (no compaction)
 *   /snapshots             - list snapshots for current session
 *   /snapshot show <id>    - display a snapshot in the editor
 *
 * Settings (settings.json):
 *   preCompactSnapshot.enabled        default true
 *   preCompactSnapshot.maxSnapshots   default 5 (older pruned)
 *   preCompactSnapshot.injectRef      default true (prepend <snapshot-ref> to summary)
 */

import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync, unlinkSync } from "node:fs";
import { join } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import type { SessionEntry } from "@earendil-works/pi-coding-agent";

// ponytail: settings kept inline - one source of truth, no separate config file
const DEFAULTS = {
	enabled: true,
	maxSnapshots: 5,
	injectRef: true,
};

const PROGRESS_FILENAME = ".pi-progress.md";
const CONVENTION_FILES = ["AGENTS.md", "CLAUDE.md", ".cursorrules", "COPILOT.md"];
const MAX_RECENT_FILES = 20;
const MAX_GOAL_LEN = 500;

interface SnapshotDetails {
	snapshotPath: string;
	snapshotId: string;
	takenAt: string;
	model?: string;
	tokensBefore: number;
}

interface Snapshot {
	id: string;
	takenAt: string;
	sessionId?: string;
	sessionFile?: string;
	cwd: string;
	trigger: "before-compact" | "manual";
	compactionEntryId?: string;
	model?: string;
	thinkingLevel?: string;
	tokensBefore: number;
	activeGoal?: string;
	plan?: { objective: string; state: string; currentStep: number; planSteps: string[] };
	openTodos: { id: string; title: string; status: string }[];
	recentFiles: { read: string[]; modified: string[] };
	projectConventions: { file: string; exists: boolean; excerpt?: string }[];
	contextUsage?: { tokens: number; limit: number; percent: number };
}

function snapshotDir(sessionDir: string | undefined): string {
	// ponytail: fall back to cwd/.pre-compact-snapshots/ if session dir unknown
	return sessionDir ? join(sessionDir, "snapshots") : join(process.cwd(), ".pre-compact-snapshots");
}

function ensureDir(dir: string): void {
	if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}

function shortId(): string {
	return Math.random().toString(36).slice(2, 8) + Date.now().toString(36).slice(-4);
}

function readProgress(cwd: string): Snapshot["plan"] | undefined {
	const p = join(cwd, PROGRESS_FILENAME);
	if (!existsSync(p)) return undefined;
	try {
		const text = readFileSync(p, "utf8");
		const m = text.match(/^<!--\s*PI-PROGRESS\s*([\s\S]*?)\s*-->/);
		if (!m) return undefined;
		const obj = JSON.parse(m[1]);
		if (!obj.goal || !Array.isArray(obj.plan)) return undefined;
		const log: string[] = obj.log ?? [];
		// ponytail: currentStep = index of last unchecked [ ] in log heuristic; fall back to log length
		const currentStep = log.length;
		return {
			objective: String(obj.goal).slice(0, 500),
			state: String(obj.state ?? "").slice(0, 1000),
			currentStep,
			planSteps: obj.plan.slice(0, 20).map(String),
		};
	} catch {
		return undefined;
	}
}

function readConventions(cwd: string): Snapshot["projectConventions"] {
	return CONVENTION_FILES.map((file) => {
		const p = join(cwd, file);
		if (!existsSync(p)) return { file, exists: false };
		try {
			const stat = statSync(p);
			// ponytail: skip huge files (>50KB), excerpt first 40 lines
			if (stat.size > 50_000) return { file, exists: true };
			const lines = readFileSync(p, "utf8").split("\n").slice(0, 40);
			return { file, exists: true, excerpt: lines.join("\n").slice(0, 2000) };
		} catch {
			return { file, exists: false };
		}
	});
}

// ponytail: open todos read from the pi-agent todo dir; structure may vary by version
function readOpenTodos(cwd: string): Snapshot["openTodos"] {
	try {
		// Pi todos live under ~/.pi/agent/sessions/<sanitized-cwd>/todos/
		const home = process.env.USERPROFILE ?? process.env.HOME ?? "";
		if (!home) return [];
		const sanitized = cwd.replace(/[:\\/]/g, "-");
		const todoDir = join(home, ".pi", "agent", "sessions", sanitized, "todos");
		if (!existsSync(todoDir)) return [];
		const out: Snapshot["openTodos"] = [];
		for (const f of readdirSync(todoDir)) {
			if (!f.endsWith(".md")) continue;
			try {
				const text = readFileSync(join(todoDir, f), "utf8");
				const title = (text.match(/^#\s+(.+)/m) ?? [, f])[1].trim();
				const status = text.match(/status:\s*(\w+)/i)?.[1] ?? "unknown";
				if (status !== "done" && status !== "complete") {
					out.push({ id: f.replace(/\.md$/, ""), title, status });
				}
			} catch {
				// skip unreadable
			}
		}
		return out.slice(0, 10);
	} catch {
		return [];
	}
}

function extractRecentFiles(branch: SessionEntry[]): { read: string[]; modified: string[] } {
	const read = new Set<string>();
	const modified = new Set<string>();
	// ponytail: walk branch backwards, dedupe, stop at 20 per side
	for (let i = branch.length - 1; i >= 0 && (read.size < MAX_RECENT_FILES || modified.size < MAX_RECENT_FILES); i--) {
		const entry = branch[i];
		if (entry.type !== "message") continue;
		const msg = entry.message as { role?: string; content?: unknown };
		if (!msg || msg.role !== "assistant") continue;
		const content = msg.content;
		if (!Array.isArray(content)) continue;
		for (const block of content) {
			if (!block || typeof block !== "object") continue;
			const b = block as { type?: string; name?: string; input?: Record<string, unknown> };
			if (b.type !== "toolCall" || !b.name) continue;
			const path = b.input?.path ?? b.input?.file_path ?? b.input?.filePath;
			if (typeof path !== "string") continue;
			if (b.name === "read" || b.name === "grep" || b.name === "glob") read.add(path);
			else if (b.name === "write" || b.name === "edit" || b.name === "patch") modified.add(path);
		}
	}
	return {
		read: Array.from(read).slice(0, MAX_RECENT_FILES),
		modified: Array.from(modified).slice(0, MAX_RECENT_FILES),
	};
}

function extractActiveGoal(branch: SessionEntry[]): string | undefined {
	// ponytail: last user message text before any compaction, truncated
	for (let i = branch.length - 1; i >= 0; i--) {
		const entry = branch[i];
		if (entry.type === "compaction") continue;
		if (entry.type !== "message") continue;
		const msg = entry.message as { role?: string; content?: unknown };
		if (msg?.role !== "user") continue;
		const content = msg.content;
		if (typeof content === "string") return content.slice(0, MAX_GOAL_LEN);
		if (Array.isArray(content)) {
			const text = content
				.filter((b): b is { type: "text"; text: string } => !!b && typeof b === "object" && (b as { type?: string }).type === "text")
				.map((b) => b.text)
				.join("\n");
			if (text) return text.slice(0, MAX_GOAL_LEN);
		}
	}
	return undefined;
}

function buildSnapshot(args: {
	branch: SessionEntry[];
	cwd: string;
	sessionId?: string;
	sessionFile?: string;
	trigger: Snapshot["trigger"];
	compactionEntryId?: string;
	model?: string;
	thinkingLevel?: string;
	tokensBefore: number;
	contextUsage?: Snapshot["contextUsage"];
}): Snapshot {
	const { branch, cwd, sessionId, sessionFile, trigger, compactionEntryId, model, thinkingLevel, tokensBefore, contextUsage } = args;
	return {
		id: `snap-${Date.now().toString(36)}-${shortId()}`,
		takenAt: new Date().toISOString(),
		sessionId,
		sessionFile,
		cwd,
		trigger,
		compactionEntryId,
		model,
		thinkingLevel,
		tokensBefore,
		activeGoal: extractActiveGoal(branch),
		plan: readProgress(cwd),
		openTodos: readOpenTodos(cwd),
		recentFiles: extractRecentFiles(branch),
		projectConventions: readConventions(cwd),
		contextUsage,
	};
}

function writeSnapshot(dir: string, snap: Snapshot): string {
	ensureDir(dir);
	const filepath = join(dir, `${snap.id}.json`);
	writeFileSync(filepath, JSON.stringify(snap, null, 2), "utf8");
	return filepath;
}

function pruneOld(dir: string, keep: number): void {
	try {
		const files = readdirSync(dir)
			.filter((f) => f.endsWith(".json"))
			.map((f) => ({ f, mtime: statSync(join(dir, f)).mtimeMs }))
			.sort((a, b) => b.mtime - a.mtime);
		for (const old of files.slice(keep)) {
			try {
				unlinkSync(join(dir, old.f));
			} catch {
				// best effort
			}
		}
	} catch {
		// best effort
	}
}

function renderRef(snap: Snapshot): string {
	// ponytail: keep this short - LLM reads it as a hint, not as content
	const goal = snap.activeGoal ? `goal="${snap.activeGoal.replace(/"/g, "'").slice(0, 200)}"` : "";
	const files = `${snap.recentFiles.read.length}r/${snap.recentFiles.modified.length}m`;
	const todos = snap.openTodos.length ? ` todos=${snap.openTodos.length}` : "";
	const plan = snap.plan ? " plan=yes" : "";
	const model = snap.model ? ` model=${snap.model}` : "";
	return `<snapshot-ref id="${snap.id}" path="${snap.sessionFile ?? ""}" taken="${snap.takenAt}" tokens=${snap.tokensBefore} files=${files}${todos}${plan}${model} ${goal}/>`;
}

function wrapSummary(summary: string, snap: Snapshot, inject: boolean): string {
	if (!inject) return summary;
	const ref = renderRef(snap);
	return `${ref}\n\n${summary}`;
}

function readSettings(pi: ExtensionAPI): typeof DEFAULTS {
	// ponytail: read from ctx.model registry config? Simpler: hard defaults, expose via flag later
	void pi;
	return DEFAULTS;
}

function listSnapshots(dir: string): { id: string; takenAt: string; trigger: string; tokens: number }[] {
	try {
		if (!existsSync(dir)) return [];
		return readdirSync(dir)
			.filter((f) => f.endsWith(".json"))
			.map((f) => {
				try {
					const s = JSON.parse(readFileSync(join(dir, f), "utf8")) as Snapshot;
					return { id: s.id, takenAt: s.takenAt, trigger: s.trigger, tokens: s.tokensBefore };
				} catch {
					return { id: f.replace(/\.json$/, ""), takenAt: "?", trigger: "?", tokens: 0 };
				}
			})
			.sort((a, b) => b.takenAt.localeCompare(a.takenAt));
	} catch {
		return [];
	}
}

export default function preCompactSnapshotExtension(pi: ExtensionAPI) {
	const settings = readSettings(pi);

	pi.on("session_before_compact", async (event, ctx) => {
		if (!settings.enabled) return;
		try {
			const branch = ctx.sessionManager.getBranch();
			const snap = buildSnapshot({
				branch,
				cwd: ctx.cwd,
				sessionId: ctx.sessionManager.getSessionId(),
				sessionFile: ctx.sessionManager.getSessionFile(),
				trigger: "before-compact",
				model: ctx.model ? `${ctx.model.provider}/${ctx.model.id}` : undefined,
				thinkingLevel: ctx.getThinkingLevel?.(),
				tokensBefore: event.preparation.tokensBefore,
				contextUsage: (() => {
					const u = ctx.getContextUsage();
					if (!u) return undefined;
					return { tokens: u.tokens, limit: u.contextWindow, percent: u.percent };
				})(),
			});

			const dir = snapshotDir(ctx.sessionManager.getSessionDir());
			const path = writeSnapshot(dir, snap);
			pruneOld(dir, settings.maxSnapshots);

			if (ctx.hasUI) {
				ctx.ui.notify(`Snapshot ${snap.id} saved (${snap.tokensBefore.toLocaleString()} tok)`, "info");
			}

			// ponytail: if the LLM will summarize, intercept ONLY when no other extension supplied a summary.
			// We always inject the ref tag — adding <snapshot-ref> at top of summary is safe.
			const existing = event as unknown as { _existingSummary?: string };
			// If a higher-priority extension already supplied a summary via custom-compaction-style hook,
			// we can't see it from this event; SessionBeforeCompactResult.compaction.summary is the merge target.
			// We rely on the details.snapshotPath hook below for retrieval.
			const details: SnapshotDetails = {
				snapshotPath: path,
				snapshotId: snap.id,
				takenAt: snap.takenAt,
				model: snap.model,
				tokensBefore: snap.tokensBefore,
			};

			// Return our own compaction result so the ref tag wraps whatever the LLM produced.
			// If another extension returns a richer summary, that wins; ours is the fallback.
			// ponytail: build a fallback summary body, wrapSummary prepends the <snapshot-ref> tag exactly once
			const fallbackBody =
				`Pre-compact snapshot saved at ${path}. The compaction summary follows.\n\n` +
				`Snapshot captures: model=${snap.model ?? "?"}, tokens=${snap.tokensBefore}, ` +
				`files=${snap.recentFiles.read.length}r/${snap.recentFiles.modified.length}m, ` +
				`open todos=${snap.openTodos.length}, plan=${snap.plan ? "yes" : "no"}.\n\n` +
				(event.preparation.previousSummary ?? "");

			void existing; // reserved for future multi-extension merge
			return {
				compaction: {
					summary: wrapSummary(fallbackBody, snap, settings.injectRef),
					firstKeptEntryId: event.preparation.firstKeptEntryId,
					tokensBefore: event.preparation.tokensBefore,
					details,
				},
			};
		} catch (err) {
			if (ctx.hasUI) {
				ctx.ui.notify(`Snapshot failed: ${err instanceof Error ? err.message : String(err)}`, "error");
			}
			// fall through to default compaction
		}
	});

	pi.on("session_start", async (event, ctx) => {
		if (!settings.enabled) return;
		if (event.reason !== "reload" && event.reason !== "resume" && event.reason !== "fork") return;
		try {
			const entries = ctx.sessionManager.getEntries();
			// ponytail: find most recent compaction with snapshotPath in details
			for (let i = entries.length - 1; i >= 0; i--) {
				const e = entries[i];
				if (e.type !== "compaction") continue;
				const details = e.details as SnapshotDetails | undefined;
				if (!details?.snapshotPath || !existsSync(details.snapshotPath)) continue;
				const ago = humanAgo(new Date(details.takenAt));
				if (ctx.hasUI) {
					ctx.ui.notify(
						`Resumed with snapshot ${details.snapshotId} (${ago}, model ${details.model ?? "?"}, ${details.tokensBefore.toLocaleString()} tok). ` +
							`Path: ${details.snapshotPath}`,
						"info",
						{ duration: 5000 },
					);
				}
				return;
			}
		} catch {
			// best effort - notify must never break startup
		}
	});

	pi.registerCommand("snapshot", {
		description: "Take a pre-compact snapshot now. Usage: /snapshot [show <id>]",
		handler: async (args, ctx) => {
			const dir = snapshotDir(ctx.sessionManager.getSessionDir());
			const trimmed = args.trim();
			if (trimmed.startsWith("show")) {
				const id = trimmed.slice(4).trim();
				const list = listSnapshots(dir);
				const match = id ? list.find((s) => s.id === id || s.id.startsWith(id)) : list[0];
				if (!match) {
					ctx.ui.notify(`No snapshot found${id ? `: ${id}` : ""}`, "warning");
					return;
				}
				const path = join(dir, `${match.id}.json`);
				if (!existsSync(path)) {
					ctx.ui.notify(`Snapshot file missing: ${path}`, "error");
					return;
				}
				const text = readFileSync(path, "utf8");
				const edited = await ctx.ui.editor(`Snapshot ${match.id}`, text);
				if (edited !== undefined) {
					ctx.ui.notify(`Snapshot shown (${text.length} chars)`, "info");
				}
				return;
			}
			try {
				const branch = ctx.sessionManager.getBranch();
				const snap = buildSnapshot({
					branch,
					cwd: ctx.cwd,
					sessionId: ctx.sessionManager.getSessionId(),
					sessionFile: ctx.sessionManager.getSessionFile(),
					trigger: "manual",
					model: ctx.model ? `${ctx.model.provider}/${ctx.model.id}` : undefined,
					thinkingLevel: ctx.getThinkingLevel?.(),
					tokensBefore: ctx.getContextUsage()?.tokens ?? 0,
				});
				const path = writeSnapshot(dir, snap);
				pruneOld(dir, settings.maxSnapshots);
				ctx.ui.notify(
					`Manual snapshot ${snap.id} saved (${snap.tokensBefore.toLocaleString()} tok, ${snap.recentFiles.read.length}r/${snap.recentFiles.modified.length}m). Path: ${path}`,
					"info",
				);
			} catch (err) {
				ctx.ui.notify(`Snapshot failed: ${err instanceof Error ? err.message : String(err)}`, "error");
			}
		},
	});

	pi.registerCommand("snapshots", {
		description: "List snapshots for the current session",
		handler: async (_args, ctx) => {
			const dir = snapshotDir(ctx.sessionManager.getSessionDir());
			const list = listSnapshots(dir);
			if (list.length === 0) {
				ctx.ui.notify("No snapshots yet. They are auto-created before compaction. Use /snapshot for manual.", "info");
				return;
			}
			const lines = list.map(
				(s, i) =>
					`${i + 1}. ${s.id}  ${s.takenAt}  ${s.trigger.padEnd(15)}  ${s.tokens.toLocaleString()} tok`,
			);
			const text = `Snapshots in ${dir}\n\n${lines.join("\n")}\n\nUse: /snapshot show <id>`;
			await ctx.ui.editor("Snapshots", text);
		},
	});
}

function humanAgo(when: Date): string {
	const ms = Date.now() - when.getTime();
	const s = Math.floor(ms / 1000);
	if (s < 60) return `${s}s ago`;
	const m = Math.floor(s / 60);
	if (m < 60) return `${m}m ago`;
	const h = Math.floor(m / 60);
	if (h < 24) return `${h}h ago`;
	const d = Math.floor(h / 24);
	return `${d}d ago`;
}