/**
 * Claude CLI session collector — SQLite (context-mode) + JSONL fallback.
 *
 * Primary source: SQLite in ~/.claude/context-mode/sessions/
 * Schema:
 *   session_events(id, session_id, type, category, data, created_at, ...)
 *     types: user_prompt, role, intent, file_read, file_write, file_edit,
 *            file_glob, file_search, git, sandbox-execute, decision,
 *            task_update, skill, external_ref, rule, rule_content, session_start, ...
 *   session_meta(session_id, project_dir, started_at, last_event_at, event_count)
 *   tool_calls(session_id, tool, calls, bytes_returned, updated_at)
 *
 * Fallback: JSONL in ~/.claude/projects/{project}/*.jsonl for non-SQLite sessions.
 */
import path from "node:path";
import fs from "node:fs/promises";
import { BaseCollector } from "../base/collector.mjs";
import { resolvePath } from "../base/platform.mjs";

// Session-event types to capture for behavioral analysis
const CAPTURE_TYPES = new Set([
	"user_prompt", "role", "intent",
	"file_read", "file_write", "file_edit", "file_glob", "file_search",
	"git", "sandbox-execute", "decision", "task_update",
	"skill", "external_ref", "rule", "rule_content",
	"session_start", "session_compact",
	"constraint_discovered", "intent_confirmed",
]);

export class ClaudeCliCollector extends BaseCollector {
	constructor(exportDir) {
		super({
			source: "claude-cli",
			source_type: "ai_session",
			session_root: resolvePath("~/.claude"),
			export_dir: exportDir,
		});
	}

	/** Probe: find all SQLite session databases */
	async probe() {
		const ctxDir = path.join(this.sessionRoot, "context-mode", "sessions");
		const results = [];

		let entries;
		try {
			entries = await fs.readdir(ctxDir);
		} catch {
			return [];
		}

		for (const entry of entries) {
			if (entry.endsWith(".db")) {
				results.push(path.join(ctxDir, entry));
			}
		}
		return results.sort();
	}

	async extractEvents(file) {
		const events = [];
		const db = await import("better-sqlite3").then((m) => new m.default(file));

		try {
			// Get session metadata
			const metaRows = db
				.prepare("SELECT session_id, project_dir, started_at, last_event_at, event_count FROM session_meta")
				.all();

			for (const meta of metaRows) {
				const sessionId = meta.session_id ?? path.basename(file, ".db");
				const projectDir = meta.project_dir ?? "";

				// Session-level event
				events.push(
					this.buildEvent({
						timestamp: meta.started_at
							? new Date(meta.started_at).getTime()
							: Date.now(),
						content_type: "session_meta",
						content: `session: ${sessionId} | project: ${projectDir} | events: ${meta.event_count}`,
						session_id: sessionId,
						metadata: {
							role: "session",
							project_dir: projectDir,
							event_count: meta.event_count,
							compact_count: meta.compact_count,
						},
					})
				);

				// Tool calls summary — only if tool_calls table exists in this DB
			const toolTableExists = db
				.prepare(
					"SELECT name FROM sqlite_master WHERE type='table' AND name='tool_calls'"
				)
				.get();
			if (toolTableExists) {
				const toolRows = db
					.prepare("SELECT tool, calls, bytes_returned FROM tool_calls WHERE session_id = ?")
					.all(meta.session_id);

				for (const tc of toolRows) {
					events.push(
					this.buildEvent({
							timestamp: tc.updated_at
								? new Date(tc.updated_at).getTime()
								: Date.now(),
							content_type: "tool_call",
							content: `[tool:${tc.tool}] ${tc.calls ?? ""}`,
							session_id: sessionId,
							metadata: {
								role: "assistant",
								tool: tc.tool,
								calls: tc.calls,
								bytes_returned: tc.bytes_returned,
							},
						})
					);
				}
			}
			}

			// Behavioral events from session_events
			const eventRows = db
				.prepare(
					`SELECT session_id, type, category, data, created_at
					 FROM session_events
					 WHERE type IN (${[...CAPTURE_TYPES]
						.map((t) => `'${t}'`)
						.join(",")})
					 ORDER BY created_at ASC`
				)
				.all();

			for (const ev of eventRows) {
				const content = this.#extractContent(ev.type, ev.data);
				if (!content) continue;

				events.push(
					this.buildEvent({
						timestamp: ev.created_at
							? new Date(ev.created_at).getTime()
							: Date.now(),
						content_type: ev.type,
						content,
						session_id: ev.session_id ?? path.basename(file, ".db"),
						metadata: {
							role: this.#typeToRole(ev.type),
							category: ev.category,
						},
					})
				);
			}
		} finally {
			db.close();
		}

		return events;
	}

	#typeToRole(type) {
		if (
			[
				"user_prompt",
				"session_start",
				"file_read",
				"file_glob",
				"file_search",
				"git",
				"external_ref",
			].includes(type)
		)
			return "user";
		if (["role", "intent", "decision", "rule", "rule_content"].includes(type))
			return "system";
		if (
			[
				"file_write",
				"file_edit",
				"sandbox-execute",
				"task_update",
				"skill",
				"session_compact",
			].includes(type)
		)
			return "assistant";
		return "assistant";
	}

	#extractContent(type, data) {
		if (!data) return null;
		try {
			const obj = JSON.parse(data);
			switch (type) {
				case "user_prompt":
					return typeof obj === "string" ? obj : JSON.stringify(obj).slice(0, 1000);
				case "role":
					return `role: ${obj.value ?? obj}`;
				case "intent":
					return `intent: ${obj.intent ?? obj}`;
				case "file_read":
					return `read: ${obj.path ?? JSON.stringify(obj).slice(0, 100)}`;
				case "file_write":
					return `write: ${obj.path ?? JSON.stringify(obj).slice(0, 100)}`;
				case "file_edit":
					return `edit: ${obj.path ?? JSON.stringify(obj).slice(0, 100)}`;
				case "file_glob":
					return `glob: ${obj.pattern ?? JSON.stringify(obj).slice(0, 100)}`;
				case "file_search":
					return `search: ${obj.query ?? JSON.stringify(obj).slice(0, 100)}`;
				case "git":
					return `git: ${obj.command ?? JSON.stringify(obj).slice(0, 100)}`;
				case "sandbox-execute":
					return `exec: ${obj.command ?? JSON.stringify(obj).slice(0, 100)}`;
				case "decision":
					return `decision: ${obj.decision ?? JSON.stringify(obj).slice(0, 200)}`;
				case "task_update":
					return `task: ${obj.status ?? JSON.stringify(obj).slice(0, 100)}`;
				case "skill":
					return `skill: ${obj.name ?? JSON.stringify(obj).slice(0, 100)}`;
				case "external_ref":
					return `ref: ${obj.url ?? obj.reference ?? JSON.stringify(obj).slice(0, 100)}`;
				case "rule":
					return `rule: ${obj.name ?? JSON.stringify(obj).slice(0, 100)}`;
				case "rule_content":
					return `rule_content: ${JSON.stringify(obj).slice(0, 200)}`;
				case "session_start":
					return `session_start: ${JSON.stringify(obj).slice(0, 100)}`;
				case "session_compact":
					return `session_compact: ${JSON.stringify(obj).slice(0, 100)}`;
				case "constraint_discovered":
					return `constraint: ${JSON.stringify(obj).slice(0, 150)}`;
				default:
					return JSON.stringify(obj).slice(0, 500);
			}
		} catch {
			return typeof data === "string" ? data.slice(0, 500) : null;
		}
	}
}
