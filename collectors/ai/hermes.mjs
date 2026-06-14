/**
 * Hermes session collector.
 *
 * Session structure:
 *   ~/.hermes/sessions/
 *     sessions.json              ← master index (all sessions + full message history)
 *     20260516_202116_*.jsonl   ← standalone JSONL exports
 *
 * sessions.json structure:
 *   { "session_key": { session_id, created_at, display_name, platform, messages } }
 *
 * JSONL export structure:
 *   {role, content, timestamp, tool_calls?}
 */
import path from "node:path";
import fs from "node:fs/promises";
import { BaseCollector } from "../base/collector.mjs";
import { resolvePath } from "../base/platform.mjs";

export class HermesCollector extends BaseCollector {
	constructor(exportDir) {
		super({
			source: "hermes",
			source_type: "ai_session",
			session_root: resolvePath("~/.hermes/sessions"),
			export_dir: exportDir,
		});
	}

	async probe() {
		const sessionsJson = path.join(this.sessionRoot, "sessions.json");
		const jsonls = [];

		// Standalone JSONL exports
		let entries;
		try {
			entries = await fs.readdir(this.sessionRoot);
		} catch {
			return [];
		}
		for (const e of entries) {
			if (e.endsWith(".jsonl")) {
				jsonls.push(path.join(this.sessionRoot, e));
			}
		}

		// sessions.json is the primary source
		try {
			await fs.access(sessionsJson);
			return [sessionsJson, ...jsonls];
		} catch {
			return jsonls;
		}
	}

	async extractEvents(file) {
		const filename = path.basename(file);
		if (filename === "sessions.json") {
			return this.#extractFromIndex();
		}
		return this.#extractFromJsonl(file);
	}

	async #extractFromIndex() {
		const events = [];
		const indexPath = path.join(this.sessionRoot, "sessions.json");
		let indexData;
		try {
			const raw = await fs.readFile(indexPath, "utf8");
			indexData = JSON.parse(raw);
		} catch {
			return [];
		}

		for (const [, session] of Object.entries(indexData)) {
			const toolSequence = [];
			for (const msg of session.messages ?? []) {
				const textParts = [];
				const role = msg.role ?? "unknown";

				if (typeof msg.content === "string" && msg.content) {
					textParts.push(msg.content);
				}

				for (const tc of msg.tool_calls ?? []) {
					const tcName = tc.name ?? tc.function ?? "unknown";
					textParts.push(`[tool:${tcName}] ${JSON.stringify(tc.arguments ?? {})}`);
					toolSequence.push(tcName);
				}

				const content = textParts.join("\n").trim();
				if (!content) continue;

				const timestamp = msg.timestamp
					? new Date(msg.timestamp).getTime()
					: new Date(session.created_at).getTime();

				events.push(this.buildEvent({
					timestamp,
					content_type: "transcript",
					content,
					session_id: session.session_id ?? session.session_key ?? "unknown",
					metadata: {
						role,
						platform: session.platform,
						display_name: session.display_name,
						tool_sequence: [...new Set(toolSequence)],
					},
				}));
			}
		}
		return events;
	}

	async #extractFromJsonl(file) {
		const raw = await fs.readFile(file, "utf8");
		const lines = raw.split("\n").filter((l) => l.trim());
		const events = [];
		const toolSequence = [];

		for (const line of lines) {
			let obj;
			try {
				obj = JSON.parse(line);
			} catch {
				continue;
			}

			const role = obj.role ?? "unknown";
			const contentRaw = obj.content;
			const reasoning = obj.reasoning;
			const toolCalls = obj.tool_calls;

			const textParts = [];
			if (contentRaw) textParts.push(contentRaw);
			if (reasoning) textParts.push(`[thinking] ${reasoning}`);

			for (const tc of toolCalls ?? []) {
				const tcName = tc.name ?? tc.function ?? "unknown";
				const tcArgs = tc.arguments ?? {};
				textParts.push(`[tool:${tcName}] ${JSON.stringify(tcArgs)}`);
				toolSequence.push(tcName);
			}

			const content = textParts.join("\n").trim();
			if (!content) continue;

			const timestamp = obj.timestamp
				? new Date(obj.timestamp).getTime()
				: Date.now();

			events.push(this.buildEvent({
				timestamp,
				content_type: "transcript",
				content,
				session_id: path.basename(file, ".jsonl"),
				metadata: {
					role,
					tool_sequence: [...new Set(toolSequence)],
				},
			}));
		}
		return events;
	}
}
