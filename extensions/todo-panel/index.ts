/**
 * Todo Side Panel Extension
 *
 * Renders active todos as a widget above the editor with a progress bar.
 * Updates reactively after every turn via session_start, turn_end, agent_end.
 * Shows a "context compacted" notice for 30s after session_compact.
 *
 * Bug fixes vs. previous version:
 *  - `pi.setWidget(...)` does not exist. The correct path is `ctx.ui.setWidget(...)`.
 *  - `ExtensionAPI` does not expose UI; UI lives on the per-event `ctx`.
 *  - Guard on `ctx.hasUI` so headless / RPC modes don't throw.
 *  - Import `getAgentDir` from `@earendil-works/pi-coding-agent` (the
 *    `@mariozechner/...` alias path doesn't exist in this npm layout).
 *  - Add a true progress bar driven by completed vs total todos.
 *  - Hook `session_compact` to surface the lost-state risk to the user.
 */

import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { getAgentDir } from "@earendil-works/pi-coding-agent";
import { readdirSync, readFileSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";

interface TodoFM {
	id: string;
	title: string;
	tags?: string[];
	status: string;
	created_at: string;
	closed_at?: string;
}

function encodeCwdPath(cwd: string): string {
	// Mirror pi's encodeCwdPath (sanitize separators and colons, keep casing)
	return `--${cwd.replace(/^[/\\]/, "").replace(/[/\\:]/g, "-")}--`;
}

function getTodosDir(cwd: string): string {
	const override = process.env.PI_TODO_PATH;
	if (override && override.trim()) return resolve(cwd, override.trim());
	return join(getAgentDir(), "sessions", encodeCwdPath(cwd), "todos");
}

function parseTodoFile(path: string): TodoFM | null {
	try {
		const text = readFileSync(path, "utf8");
		const m = text.match(/^(\{[\s\S]*?\})\s*\n/);
		if (!m) return null;
		return JSON.parse(m[1]) as TodoFM;
	} catch {
		return null;
	}
}

interface TodoStats {
	active: TodoFM[];
	done: number;
	total: number;
	pct: number;
}

function loadAllTodos(cwd: string): TodoStats {
	const dir = getTodosDir(cwd);
	if (!existsSync(dir)) return { active: [], done: 0, total: 0, pct: 0 };
	const files = readdirSync(dir).filter((f) => f.endsWith(".md") && !f.endsWith(".lock"));
	const all: TodoFM[] = [];
	for (const f of files) {
		const t = parseTodoFile(join(dir, f));
		if (t) all.push(t);
	}
	const done = all.filter((t) => t.status === "done" || t.status === "closed").length;
	const active = all.filter((t) => t.status !== "done" && t.status !== "closed");
	const order: Record<string, number> = { in_progress: 0, open: 1, blocked: 2 };
	active.sort((a, b) => {
		const sa = order[a.status] ?? 3;
		const sb = order[b.status] ?? 3;
		if (sa !== sb) return sa - sb;
		return (b.created_at || "").localeCompare(a.created_at || "");
	});
	const total = all.length;
	const pct = total > 0 ? Math.round((done / total) * 100) : 0;
	return { active, done, total, pct };
}

function renderWidget(stats: TodoStats): string[] {
	const lines: string[] = [];
	const innerW = 32;
	const barWidth = 24;
	const filled = Math.round((stats.pct / 100) * barWidth);
	const bar = "█".repeat(filled) + "░".repeat(Math.max(0, barWidth - filled));
	const label = `TODOS ${stats.done}/${stats.total} ${stats.pct}%`;

	lines.push(`┌─ ${label}${"─".repeat(Math.max(1, innerW - label.length - 1))}┐`);
	lines.push(`│ ${bar}${" ".repeat(Math.max(0, innerW - barWidth - 1))}│`);

	const showCount = Math.min(stats.active.length, 5);
	if (stats.total === 0) {
		const msg = " no todos · use /todos";
		lines.push(`│${msg.padEnd(innerW + 1)}│`);
	} else if (showCount === 0) {
		const msg = " all done ✓";
		lines.push(`│${msg.padEnd(innerW + 1)}│`);
	} else {
		for (const t of stats.active.slice(0, showCount)) {
			const id = t.id.slice(0, 6);
			const icon = t.status === "in_progress" ? "●" : t.status === "blocked" ? "⊘" : "○";
			const titleMax = innerW - 10;
			const title = t.title.length > titleMax ? t.title.slice(0, titleMax - 1) + "…" : t.title;
			const row = ` ${icon} ${id} ${title}`;
			lines.push(`│${row.padEnd(innerW + 1)}│`);
		}
		if (stats.active.length > showCount) {
			const more = ` … +${stats.active.length - showCount} more`;
			lines.push(`│${more.padEnd(innerW + 1)}│`);
		}
	}
	lines.push(`└${"─".repeat(innerW + 1)}┘`);
	return lines;
}

function renderCompactionNotice(): string[] {
	const innerW = 32;
	return [
		`┌─ ${"⚠ CONTEXT COMPACTED"}${"─".repeat(Math.max(1, innerW - 18))}┐`,
		`│ ${"Review the new prefix;".padEnd(innerW)} │`,
		`│ ${"state may be lost.".padEnd(innerW)} │`,
		`└${"─".repeat(innerW + 1)}┘`,
	];
}

export default function todoPanelExtension(pi: ExtensionAPI) {
	// Captured per event so the debounced render uses the freshest ctx.
	let lastCtx: ExtensionContext | null = null;
	let lastCwd = "";
	let lastCompactionTs = 0;
	let renderTimer: ReturnType<typeof setTimeout> | null = null;

	const render = () => {
		const ctx = lastCtx;
		if (!ctx || !ctx.hasUI) return;
		if (!lastCwd) return;
		try {
			const stats = loadAllTodos(lastCwd);
			const showCompaction = Date.now() - lastCompactionTs < 30_000;
			const base = renderWidget(stats);
			const lines = showCompaction ? [...base, ...renderCompactionNotice()] : base;
			ctx.ui.setWidget("todo-panel", lines.length ? lines : undefined, {
				placement: "aboveEditor",
			});
		} catch (error) {
			const message = error instanceof Error ? error.message : String(error);
			lastCtx?.ui.notify(`Todo panel failed: ${message}`, "error");
		}
	};

	const scheduleRender = (ctx: ExtensionContext) => {
		lastCtx = ctx;
		if (ctx.cwd) lastCwd = ctx.cwd;
		if (renderTimer) clearTimeout(renderTimer);
		renderTimer = setTimeout(render, 50);
	};

	pi.on("session_start", scheduleRender);
	pi.on("turn_end", scheduleRender);
	pi.on("agent_end", scheduleRender);
	pi.on("turn_start", scheduleRender);

	pi.registerCommand("todo-panel", {
		description: "Refresh the persistent todo panel",
		handler: async (_args, ctx) => {
			scheduleRender(ctx);
			ctx.ui.notify(`Todo panel refreshed for ${getTodosDir(ctx.cwd)}`, "info");
		},
	});

	pi.on("session_compact", (_event, ctx) => {
		lastCompactionTs = Date.now();
		scheduleRender(ctx);
	});
}
