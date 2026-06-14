/**
 * BaseCollector — abstract base for all connectors.
 *
 * Each connector:
 *  1. Implements `probe()` — returns session file paths
 *  2. Implements `extractEvents(file)` — maps one session file to UnifiedEvent[]
 *  3. Call `run()` to execute the full collect → export cycle
 *
 * Handles: incremental collection (tracks last-seen files),
 * event_hash dedup, platform-aware paths, export JSONL writing.
 */
import fsSync from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import { getDeviceId, resolvePath } from "./platform.mjs";
import { computeEventHash, serializeMetadata, uuid } from "./schema.mjs";

/**
 * @param {Object} config
 * @param {string} config.source  — 'pi', 'chrome', 'whatsapp'
 * @param {string} config.source_type  — 'ai_session', 'browser', etc.
 * @param {string} config.session_root  — directory to scan
 * @param {string} [config.export_dir]  — defaults to ~/.memory/exports/{source}/
 */
export class BaseCollector {
	#source;
	#source_type;
	#sessionRoot;
	#exportDir;
	#stateFile;
	deviceId;

	constructor(config) {
		this.#source = config.source;
		this.#source_type = config.source_type;
		this.#sessionRoot = resolvePath(config.session_root);
		this.deviceId = getDeviceId();

		// Resolve export dir from session_root home expansion
		const homeExpanded = this.#sessionRoot.startsWith("~")
			? path.join(process.env.HOME ?? process.env.USERPROFILE ?? "", this.#sessionRoot.slice(1))
			: this.#sessionRoot;

		this.#exportDir = config.export_dir
			?? path.join(path.dirname(homeExpanded), ".memory", "exports", this.#source);

		this.#stateFile = path.join(this.#exportDir, `.${this.#source}.state.json`);
	}

	get source() { return this.#source; }
	get exportDir() { return this.#exportDir; }
	get sessionRoot() { return this.#sessionRoot; }

	/**
	 * Find all session files. Override for custom discovery.
	 */
	async probe() {
		return findFiles(this.#sessionRoot);
	}

	/**
	 * Extract unified events from one session file.
	 * Must be implemented per-connector.
	 * @param {string} file
	 * @returns {Promise<UnifiedEvent[]>}
	 */
	async extractEvents(file) {
		throw new Error(`extractEvents not implemented for ${this.#source}`);
	}

	/**
	 * Run one collection cycle.
	 */
	async run() {
		const state = await this.#loadState();
		const files = await this.probe();
		const seen = new Set(state.files ?? []);

		const newFiles = files.filter((f) => !seen.has(f));
		if (newFiles.length === 0) {
			return { collected: 0, newFiles: 0, exportDir: this.#exportDir };
		}

		await fs.mkdir(this.#exportDir, { recursive: true });

		const exportFile = path.join(
			this.#exportDir,
			`${this.#source}_${Date.now()}.jsonl`
		);
		let count = 0;

		for (const file of newFiles) {
			const events = await this.extractEvents(file);
			for (const event of events) {
				await this.#appendEvent(exportFile, event);
				count++;
			}
			seen.add(file);
		}

		state.files = [...seen];
		state.lastRun = Date.now();
		await fs.mkdir(path.dirname(this.#stateFile), { recursive: true });
		await fs.writeFile(this.#stateFile, JSON.stringify(state), "utf8");

		return { collected: count, newFiles: newFiles.length, exportFile };
	}

	/**
	 * Build a UnifiedEvent. Subclasses call this, add source-specific metadata.
	 */
	buildEvent({ timestamp, content_type, content, session_id, metadata = {} }) {
		return {
			id: uuid(),
			timestamp,
			content_type,
			content,
			source: this.#source,
			source_type: this.#source_type,
			device_id: this.deviceId,
			session_id,
			event_hash: computeEventHash(this.#source, session_id, timestamp, content),
			metadata: serializeMetadata(metadata),
		};
	}

	// ── Private ──────────────────────────────────────────────────────────────

	async #loadState() {
		try {
			const raw = await fs.readFile(this.#stateFile, "utf8");
			return JSON.parse(raw);
		} catch {
			return { files: [], lastRun: 0 };
		}
	}

	async #appendEvent(exportFile, event) {
		const line = JSON.stringify(event) + "\n";
		await fs.appendFile(exportFile, line, "utf8");
	}
}

/**
 * Find all .jsonl files in a directory recursively.
 */
async function findFiles(dir, { ext = ".jsonl", recursive = true } = {}) {
	const results = [];

	async function walk(current) {
		let entries;
		try {
			entries = await fsSync.promises.readdir(current, { withFileTypes: true });
		} catch {
			return;
		}
		for (const entry of entries) {
			const full = path.join(current, entry.name);
			if (entry.isDirectory() && recursive) {
				await walk(full);
			} else if (entry.isFile() && entry.name.endsWith(ext)) {
				results.push(full);
			}
		}
	}

	await walk(dir);
	results.sort();
	return results;
}
