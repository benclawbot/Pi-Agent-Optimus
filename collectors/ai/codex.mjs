/**
 * OpenAI Codex session collector.
 *
 * Session structure:
 *   ~/.codex/sessions/
 *     2026/
 *       {MM}/
 *         {DD}/
 *           rollout-{timestamp}-{id}.jsonl
 *
 * JSONL entry: { timestamp, type, payload }
 *   type = 'session_meta'  → metadata
 *   type = 'event_msg'      → task_started / task_completed
 *   type = 'response_item'  → message / tool_use / tool_result
 */
import path from "node:path";
import fs from "node:fs/promises";
import { BaseCollector } from "../base/collector.mjs";
import { resolvePath } from "../base/platform.mjs";

export class CodexCollector extends BaseCollector {
	constructor(exportDir) {
		super({
			source: "codex",
			source_type: "ai_session",
			session_root: resolvePath("~/.codex/sessions"),
			export_dir: exportDir,
		});
	}

	async probe() {
		const sessionsDir = this.sessionRoot;
		const results = [];

		let years;
		try {
			years = await fs.readdir(sessionsDir);
		} catch {
			return [];
		}

		for (const year of years) {
			const yearPath = path.join(sessionsDir, year);
			let months;
			try {
				months = await fs.readdir(yearPath);
			} catch {
				continue;
			}
			for (const month of months) {
				const monthPath = path.join(yearPath, month);
				let days;
				try {
					days = await fs.readdir(monthPath);
				} catch {
					continue;
				}
				for (const day of days) {
					const dayPath = path.join(monthPath, day);
					const files = await this.#findRollouts(dayPath);
					results.push(...files);
				}
			}
		}
		return results;
	}

	async extractEvents(file) {
		const raw = await fs.readFile(file, "utf8");
		const lines = raw.split("\n").filter((l) => l.trim());
		const events = [];
		let sessionMeta = null;

		for (const line of lines) {
			let entry;
			try {
				entry = JSON.parse(line);
			} catch {
				continue;
			}

			if (entry.type === "session_meta") {
				const payload = entry.payload ?? {};
				sessionMeta = {
					id: payload.id ?? path.basename(file, ".jsonl"),
					cwd: payload.cwd ?? "",
					originator: payload.originator ?? "",
					model_provider: payload.model_provider ?? "",
					cli_version: payload.cli_version ?? "",
				};
				events.push(this.buildEvent({
					timestamp: new Date(entry.timestamp).getTime(),
					content_type: "structured",
					content: `codex_session: ${sessionMeta.cwd} | model=${sessionMeta.model_provider} | ${sessionMeta.originator}`,
					session_id: sessionMeta.id,
					metadata: sessionMeta,
				}));
				continue;
			}

			if (entry.type === "response_item") {
				const payload = entry.payload ?? {};
				const blockType = payload.type;
				if (blockType !== "message") continue;

				const contentBlocks = payload.content ?? [];
				const role = payload.role ?? "unknown";

				const textParts = [];
				for (const block of contentBlocks) {
					const btype = block.type;
					if (btype === "input_text" && block.text) {
						textParts.push(block.text);
					} else if (btype === "text" && block.text) {
						textParts.push(block.text);
					} else if (btype === "tool_use" || btype === "function_call") {
						const name = block.name ?? block.function ?? "fn";
						const args = block.input ?? {};
						textParts.push(`[tool:${name}] ${JSON.stringify(args)}`);
					} else if (btype === "tool_result") {
						const content2 = block.content ?? "";
						const resultText = typeof content2 === "string" ? content2 : JSON.stringify(content2);
						textParts.push(`[tool_result] ${resultText.slice(0, 200)}`);
					}
				}

				const content = textParts.join("\n").trim();
				if (!content) continue;

				events.push(this.buildEvent({
					timestamp: new Date(entry.timestamp).getTime(),
					content_type: "transcript",
					content,
					session_id: sessionMeta?.id ?? path.basename(file, ".jsonl"),
					metadata: {
						role,
						session_cwd: sessionMeta?.cwd,
						model_provider: sessionMeta?.model_provider,
					},
				}));
			}
		}
		return events;
	}

	async #findRollouts(dir) {
		const results = [];
		try {
			const entries = await fs.readdir(dir, { withFileTypes: true });
			for (const e of entries) {
				if (e.isFile() && e.name.startsWith("rollout-") && e.name.endsWith(".jsonl")) {
					results.push(path.join(dir, e.name));
				}
			}
		} catch {
			// no access
		}
		return results;
	}
}
