/**
 * Pi session collector.
 *
 * Session structure:
 *   ~/.pi/agent/sessions/
 *     {project}/             ← session group (project name)
 *       sessions/
 *         {timestamp}_{id}.jsonl  ← one file per session
 *
 * JSONL entry types:
 *   session            — {type, version, id, timestamp, cwd}
 *   model_change       — {type, provider, modelId, timestamp}
 *   thinking_level_change
 *   message            — {type, message: {role, content: [blocks], timestamp}}
 *   compaction
 *
 * Content block types: text, thinking, toolCall, tool_result
 */
import path from "node:path";
import fs from "node:fs/promises";
import { BaseCollector } from "../base/collector.mjs";
import { resolvePath } from "../base/platform.mjs";

export class PiCollector extends BaseCollector {
	constructor(exportDir) {
		super({
			source: "pi",
			source_type: "ai_session",
			session_root: resolvePath("~/.pi/agent/sessions"),
			export_dir: exportDir,
		});
	}

	/** Pi stores sessions under {project}/sessions/*.jsonl */
		async probe() {
		const results = [];
		let topEntries;
		try {
			topEntries = await fs.readdir(this.sessionRoot);
		} catch {
			return [];
		}

		for (const entry of topEntries) {
			const projectDir = path.join(this.sessionRoot, entry);
			let files;
			try {
				files = await fs.readdir(projectDir);
			} catch {
				continue;
			}
			for (const f of files) {
				if (f.endsWith('.jsonl')) {
					results.push(path.join(projectDir, f));
				}
			}
		}
		return results.sort();
	}

	async extractEvents(file) {
		const raw = await fs.readFile(file, "utf8");
		const lines = raw.split("\n").filter((l) => l.trim());
		if (lines.length === 0) return [];

		const meta = this.#parseSessionMeta(lines[0], file);
		if (!meta) return [];

		const events = [];
		const toolSequence = [];

		for (const line of lines.slice(1)) {
			let entry;
			try {
				entry = JSON.parse(line);
			} catch {
				continue;
			}

			if (entry.type !== "message" || !entry.message) continue;

			const msg = entry.message;
			const blocks = msg.content ?? [];
			const role = msg.role ?? "unknown";
			const textParts = [];

			for (const block of blocks) {
				if (block.type === "text" && block.text) {
					textParts.push(block.text);
				} else if (block.type === "thinking" && block.thinking) {
					textParts.push(`[thinking] ${block.thinking}`);
				} else if (block.type === "toolCall" && block.toolCall) {
					const tc = block.toolCall;
					textParts.push(`[tool:${tc.name}] ${JSON.stringify(tc.arguments ?? {})}`);
					toolSequence.push(tc.name);
				} else if (block.type === "tool_result" && block.tool_result) {
					const tr = block.tool_result;
					const resultText = typeof tr.content === "string" ? tr.content : JSON.stringify(tr.content);
					textParts.push(`[tool_result:${tr.id ?? ""}] ${resultText.slice(0, 500)}`);
				}
			}

			const content = textParts.join("\n").trim();
			if (!content) continue;

			const timestamp = entry.timestamp
				? new Date(entry.timestamp).getTime()
				: meta.startedAt;

			events.push(this.buildEvent({
				timestamp,
				content_type: "transcript",
				content,
				session_id: meta.sessionId,
				metadata: {
					role,
					session_cwd: meta.cwd,
					session_model: meta.model,
					tool_sequence: [...new Set(toolSequence)],
					entry_id: entry.id,
				},
			}));
		}

		return events;
	}

	#parseSessionMeta(line, file) {
		try {
			const entry = JSON.parse(line);
			if (entry.type !== "session") return null;
			return {
				sessionId: entry.id ?? path.basename(file, ".jsonl"),
				cwd: entry.cwd ?? "",
				startedAt: entry.timestamp ? new Date(entry.timestamp).getTime() : Date.now(),
				model: undefined,
			};
		} catch {
			return null;
		}
	}
}
